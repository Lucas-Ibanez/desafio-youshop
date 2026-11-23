"""Importa os gabaritos da H1 e da H2 (T04): CSV de data/raw/ → JSONL anonimizado em data/gold/.

Uso: uv run python scripts/import_gold.py   (ou: uv run python tasks.py gold)

1. Imprime os cabeçalhos dos CSV e mapeia as colunas por nome.
2. Monta os registros (CONTEXTO 14.1) e anonimiza com data/raw/anon_map.yaml.
3. Confere as contagens das validações. Se alguma não bater, NÃO grava nada e lista as linhas
   de cada grupo para investigar a exportação (o número nunca é corrigido aqui).
4. Grava data/gold/h2_anuncios.jsonl, h1_reclamacoes.jsonl e splits.json.

Títulos da H1 vêm do slug do link no apêndice de docs/fontes/validacao-H1-reclamacoes.md
(o CSV não tem a coluna de link). Sem esse arquivo, `titulo` fica nulo.
"""

from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

from promessa.rules.normalize import normalize

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
GOLD = ROOT / "data" / "gold"
FONTES = ROOT / "docs" / "fontes"
SEED = 42

H2_COLUMNS = {
    "id": "ID",
    "familia": "Família",
    "tipo_anunciante": "Tipo de anunciante",
    "tipo_produto": "Tipo de produto",
    "texto": "Alegação (trecho)",
    "veredito": "Veredito",
    "promessa_verificavel": "Promessa verificável",
    "data_inicio": "Início da veiculação",
}
H1_COLUMNS = {
    "id": "ID",
    "publico": "Público",
    "causa_principal": "Causa principal",
    "subcausa": "Subcausa",
    "tipo_produto": "Tipo de produto",
    "cita_anuncio": "Cita anúncio ou divulgação",
    "texto": "Resumo (paráfrase)",
}
H1_OPTIONAL = {"canal": "Canal de aquisição", "categoria": "Categoria"}  # só na amostra 2

H1_EXCLUDED = {"P74", "P81", "P90", "P50", "P54"}  # duplicadas e repetições da amostra 1

CAUSA_PRINCIPAL = {
    "Promessa": "promessa",
    "Acesso/entrega": "acesso",
    "Processo de reembolso/cancelamento": "processo",
    "Fraude/cobrança não reconhecida": "fraude",
    "Outros": "outros",
}
CAUSA_TAXONOMIA = {
    "acesso": "acesso_entrega",
    "processo": "processo",
    "fraude": "fraude",
    "outros": "outros",
}
# Rótulo de subcausa da codificação manual (H1) → subcausa da taxonomia (CONTEXTO 12.1).
SUBCAUSA = {
    # promessa
    "explicita (condicao da oferta)": "condicao_da_oferta",
    "explicita (diferente do anunciado)": "diferente_do_anunciado",
    "explicita (informacao omitida na venda)": "informacao_omitida",
    "explicita (resultado prometido)": "resultado_prometido",
    "expectativa (fraca)": "qualidade_abaixo",
    "expectativa (qualidade tecnica)": "qualidade_abaixo",
    # acesso / entrega
    "acesso nao liberado": "acesso_nao_liberado",
    "liberacao gradual do conteudo": "acesso_nao_liberado",
    "extras pagos nao entregues": "acesso_nao_liberado",
    "servico nao entregue": "acesso_nao_liberado",
    "servico nao entregue (aulas)": "acesso_nao_liberado",
    "servico nao entregue (sessoes)": "acesso_nao_liberado",
    "fisico nao entregue": "fisico_nao_entregue",
    "fisico entregue com atraso": "fisico_nao_entregue",
    "fisico sem confirmacao": "fisico_nao_entregue",
    "servico nao funciona": "servico_fora_do_ar",
    "servico descontinuado": "servico_fora_do_ar",
    "modulos nao abrem": "servico_fora_do_ar",
    "download quebrado": "servico_fora_do_ar",
    "migracao de sistema": "servico_fora_do_ar",
    "login/conta": "login_conta",
    "acesso bloqueado": "login_conta",
    "acesso bloqueado por pagamento": "login_conta",
    "area de membros confusa": "login_conta",
    "conteudo/creditos removidos": "conteudo_removido",
    # processo
    "arrependimento sem motivo de produto": "arrependimento_sem_motivo",
    "sem motivo declarado": "arrependimento_sem_motivo",
    "compra por engano": "arrependimento_sem_motivo",
    "compra por engano apos abordagem de venda": "arrependimento_sem_motivo",
    "interface (cancelou pedido por engano)": "arrependimento_sem_motivo",
    "renovacao indesejada": "renovacao_indesejada",
    "cancelamento sem opcao": "cancelamento_travado",
    "cancelamento nao processado": "cancelamento_travado",
    "motivo pessoal": "motivo_pessoal",
    "motivo pessoal (financeiro)": "motivo_pessoal",
    "motivo pessoal (saude)": "motivo_pessoal",
    # fraude
    "cobranca nao reconhecida": "cobranca_nao_reconhecida",
    "cobranca nao reconhecida (renovacao)": "cobranca_nao_reconhecida",
    "compra nao reconhecida": "cobranca_nao_reconhecida",
    "compra por menor sem autorizacao": "cobranca_nao_reconhecida",
    "golpe de investimento": "golpe",
    "golpe percebido apos compra": "golpe",
    "pratica irregular do vendedor (pagamento fora do checkout)": "pagamento_fora_do_checkout",
}

EMPTY = {"", "-", "nao informado"}


# --- Leitura -----------------------------------------------------------------------------


def read_csv(name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = RAW / name
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
        return list(reader.fieldnames or []), rows


def require_columns(name: str, header: list[str], columns: dict[str, str]) -> None:
    missing = [col for col in columns.values() if col not in header]
    if missing:
        sys.exit(f"ERRO {name}: colunas ausentes {missing}. Cabeçalho: {header}")


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return None if normalize(value) in EMPTY else value


def h1_titles() -> dict[str, str]:
    """Título (palavras do comprador) a partir do slug do link no apêndice da validação H1."""
    path = FONTES / "validacao-H1-reclamacoes.md"
    if not path.exists():
        print(f"AVISO: {path.relative_to(ROOT)} ausente; `titulo` fica nulo.")
        return {}
    titles = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| [A-Z]\d\d \|", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        m = re.search(r"reclameaqui\.com\.br/[^/]+/([^/)]+)/?", cells[-1])
        if m:
            slug = m.group(1).split("_", 1)[0]  # tira o sufixo de id do Reclame Aqui
            titles[cells[0]] = re.sub(r"\s+", " ", slug.replace("-", " ")).strip()
    return titles


def appendix_names() -> list[str]:
    """Anunciantes (H2), plataformas e empresas reclamadas (H1) dos apêndices, para conferência."""
    names: set[str] = set()
    h2 = FONTES / "validacao-H2-alegacoes.md"
    h1 = FONTES / "validacao-H1-reclamacoes.md"
    for path in (h2, h1):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not re.match(r"\| [A-Z]\d\d \|", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if path == h2:
                raw = re.sub(r"\s*\((?!com )[^)]*\)\s*$", "", cells[2])
                names |= {p.strip() for p in re.split(r"\s+-\s+|\s*\(com\s+|\)", raw)}
            else:
                names.add(cells[1])
                if cells[0].startswith("P"):
                    names.add(re.sub(r"^[\d-]+", "", cells[2]).replace("-", " "))
    generic = {"plataforma"}
    return sorted(n for n in names if len(n) >= 4 and normalize(n) not in generic)


# --- Anonimização ------------------------------------------------------------------------


@dataclass
class Anonymizer:
    patterns: list[tuple[re.Pattern[str], str]]

    @classmethod
    def from_file(cls, path: Path) -> Anonymizer:
        if not path.exists():
            sys.exit(f"ERRO: {path.relative_to(ROOT)} ausente (lista de substituição).")
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        entries = [(n, "[PESSOA]") for n in data.get("pessoas", [])]
        entries += [(n, "[MARCA]") for n in data.get("marcas", [])]
        entries.sort(key=lambda e: -len(e[0]))  # frases maiores primeiro
        return cls([(_phrase(name), token) for name, token in entries])

    def __call__(self, text: str | None) -> str | None:
        """Troca nomes pelo marcador. Casa no texto normalizado, troca no original."""
        if text is None:
            return None
        for pattern, token in self.patterns:
            spans = [m.span() for m in pattern.finditer(normalize(text))]
            for start, end in reversed(spans):
                text = text[:start] + token + text[end:]
        return text


def _phrase(name: str) -> re.Pattern[str]:
    words = [re.escape(w) for w in normalize(name).split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)")


# --- Registros ---------------------------------------------------------------------------


def h2_category(tipo_produto: str, familia: str) -> str:
    t = normalize(tipo_produto)
    if any(k in t for k in ("suplement", "fitoter", "manipulad")):
        return "suplemento"
    if "cosmet" in t:
        return "cosmetico"
    if normalize(familia) == "renda":
        return "infoproduto_renda"
    return "infoproduto_outro"


def build_h2(anon: Anonymizer) -> list[dict]:
    header, rows = read_csv("h2_auditoria.csv")
    print(f"h2_auditoria.csv: {header}")
    require_columns("h2_auditoria.csv", header, H2_COLUMNS)
    out = []
    for r in rows:
        get = {k: (r[col] or "").strip() for k, col in H2_COLUMNS.items()}
        out.append(
            {
                "id": get["id"],
                "familia": get["familia"],
                "tipo_anunciante": get["tipo_anunciante"],
                "tipo_produto": anon(get["tipo_produto"]),
                "categoria": h2_category(get["tipo_produto"], get["familia"]),
                "texto": anon(get["texto"]),
                "veredito": get["veredito"],
                "nao_conforme": get["veredito"] != "Conforme",
                "irregular_evidente": get["veredito"] == "Irregular evidente",
                "promessa_verificavel": get["promessa_verificavel"] == "Sim",
                "data_inicio": clean(get["data_inicio"]),
            }
        )
    return out


def build_h1(anon: Anonymizer) -> tuple[list[dict], list[str]]:
    titles = h1_titles()
    out: list[dict] = []
    errors: list[str] = []
    for amostra, name in ((1, "h1_amostra1.csv"), (2, "h1_amostra2.csv")):
        header, rows = read_csv(name)
        print(f"{name}: {header}")
        require_columns(name, header, H1_COLUMNS)
        for r in rows:
            get = {k: (r[col] or "").strip() for k, col in H1_COLUMNS.items()}
            opt = {k: clean(r.get(col)) for k, col in H1_OPTIONAL.items()}
            rid = get["id"]
            if get["publico"] != "Comprador" or rid in H1_EXCLUDED:
                continue
            principal = CAUSA_PRINCIPAL.get(get["causa_principal"])
            subcausa_raw = normalize(get["subcausa"])
            if principal is None:
                errors.append(f"{rid}: causa principal desconhecida {get['causa_principal']!r}")
                continue
            if principal == "outros":
                subcausa = "outros"
            elif subcausa_raw in SUBCAUSA:
                subcausa = SUBCAUSA[subcausa_raw]
            else:
                errors.append(f"{rid}: subcausa sem mapeamento {get['subcausa']!r}")
                continue
            if principal == "promessa":
                causa = (
                    "promessa_expectativa"
                    if subcausa == "qualidade_abaixo"
                    else "promessa_explicita"
                )
            else:
                causa = CAUSA_TAXONOMIA[principal]
            out.append(
                {
                    "id": rid,
                    "amostra": amostra,
                    "texto": anon(get["texto"]),
                    "titulo": anon(titles.get(rid)),
                    "causa": causa,
                    "causa_principal": principal,
                    "subcausa": subcausa,
                    "canal": opt["canal"],
                    "categoria_produto": opt["categoria"],
                    "tipo_produto": clean(get["tipo_produto"]),
                    "cita_anuncio": get["cita_anuncio"] == "Sim",
                }
            )
    return out, errors


# --- Conferência -------------------------------------------------------------------------


@dataclass
class Check:
    label: str
    expected: object
    obtained: object
    ids: list[str]

    @property
    def ok(self) -> bool:
        return self.expected == self.obtained


def conference(h2: list[dict], h1: list[dict]) -> list[Check]:
    def ids(rows, pred):
        return [r["id"] for r in rows if pred(r)]

    def count(label, expected, rows, pred):
        selected = ids(rows, pred)
        return Check(label, expected, len(selected), selected)

    fam = Counter(r["familia"] for r in h2)
    checks = [
        Check("H2 anúncios", 60, len(h2), []),
        Check(
            "H2 famílias (saúde/renda/condições)",
            (37, 12, 11),
            (fam["Saúde/estética"], fam["Renda"], fam["Condições da oferta"]),
            [],
        ),
        count("H2 não conformes", 33, h2, lambda r: r["nao_conforme"]),
        Check(
            "H2 irregular evidente",
            ["S06", "S22", "S25", "S26"],
            ids(h2, lambda r: r["irregular_evidente"]),
            ids(h2, lambda r: r["irregular_evidente"]),
        ),
        count("H2 promessa verificável", 22, h2, lambda r: r["promessa_verificavel"]),
        Check("H1 compradores", 172, len(h1), []),
    ]
    for label, principal, expected in [
        ("H1 acesso", "acesso", 59),
        ("H1 processo", "processo", 55),
        ("H1 promessa", "promessa", 44),
        ("H1 fraude", "fraude", 12),
        ("H1 outros", "outros", 2),
    ]:
        checks.append(count(label, expected, h1, lambda r, p=principal: r["causa_principal"] == p))
    checks.append(
        count("H1 promessa explícita", 27, h1, lambda r: r["causa"] == "promessa_explicita")
    )
    for label, sub, expected in [
        ("H1 explícita: diferente do anunciado", "diferente_do_anunciado", 11),
        ("H1 explícita: condição da oferta", "condicao_da_oferta", 9),
        ("H1 explícita: informação omitida", "informacao_omitida", 5),
        ("H1 explícita: resultado prometido", "resultado_prometido", 2),
    ]:
        checks.append(count(label, expected, h1, lambda r, s=sub: r["subcausa"] == s))
    checks.append(
        count("H1 promessa expectativa", 17, h1, lambda r: r["causa"] == "promessa_expectativa")
    )
    return checks


def print_conference(checks: list[Check]) -> bool:
    print("\nConferência com as validações (CONTEXTO 14.1)")
    width = max(len(c.label) for c in checks)
    for c in checks:
        status = "OK" if c.ok else "DIVERGE"
        print(f"  {status:<8} {c.label:<{width}}  esperado={c.expected}  obtido={c.obtained}")
        if not c.ok and c.ids:
            print(f"           linhas do grupo para investigar: {', '.join(c.ids)}")
    return all(c.ok for c in checks)


def leaked_names(records: list[dict], names: list[str], fields: tuple[str, ...]) -> list[str]:
    hits = []
    patterns = [(n, _phrase(n)) for n in names]
    for r in records:
        for field in fields:
            value = r.get(field)
            if not value:
                continue
            for name, pattern in patterns:
                if pattern.search(normalize(value)):
                    hits.append(f"{r['id']}.{field}: {name}")
    return hits


# --- Splits ------------------------------------------------------------------------------


def stratified_split(rows: list[dict], key, n_dev: int, seed: int) -> dict[str, list[str]]:
    """Split estratificado determinístico: cota de `dev` por estrato pelo maior resto."""
    strata: dict[object, list[str]] = defaultdict(list)
    for r in rows:
        strata[key(r)].append(r["id"])
    rng = random.Random(seed)
    order = sorted(strata, key=str)
    for k in order:
        strata[k].sort()
        rng.shuffle(strata[k])
    total = len(rows)
    quotas = {k: n_dev * len(strata[k]) / total for k in order}
    alloc = {k: int(q) for k, q in quotas.items()}
    remaining = n_dev - sum(alloc.values())
    for k in sorted(order, key=lambda k: (-(quotas[k] - alloc[k]), str(k)))[:remaining]:
        alloc[k] += 1
    dev = sorted(i for k in order for i in strata[k][: alloc[k]])
    test = sorted(i for k in order for i in strata[k][alloc[k] :])
    return {"dev": dev, "test": test}


def build_splits(h2: list[dict], h1: list[dict]) -> dict:
    return {
        "seed": SEED,
        "h2": stratified_split(h2, lambda r: (r["nao_conforme"], r["familia"]), 20, SEED),
        "h1": stratified_split(h1, lambda r: r["causa_principal"], 40, SEED),
    }


# --- Saída -------------------------------------------------------------------------------


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    anon = Anonymizer.from_file(RAW / "anon_map.yaml")
    print("Cabeçalhos dos CSV")
    h2 = build_h2(anon)
    h1, errors = build_h1(anon)
    if errors:
        print("\nERRO: linhas que não foi possível mapear:")
        for e in errors:
            print(f"  {e}")
        return 1

    ok = print_conference(conference(h2, h1))

    names = appendix_names()
    leaks = leaked_names(h2, names, ("texto", "tipo_produto")) + leaked_names(
        h1, names, ("texto", "titulo")
    )
    print(f"\nAnonimização: {len(names)} nomes dos apêndices conferidos nos textos e títulos")
    for leak in leaks:
        print(f"  VAZOU {leak}")
    ok = ok and not leaks

    if not ok:
        print("\nFALHOU: nada foi gravado. Investigue a exportação; não ajuste os números aqui.")
        return 1

    GOLD.mkdir(parents=True, exist_ok=True)
    write_jsonl(GOLD / "h2_anuncios.jsonl", h2)
    write_jsonl(GOLD / "h1_reclamacoes.jsonl", h1)
    splits = build_splits(h2, h1)
    (GOLD / "splits.json").write_text(
        json.dumps(splits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    with_title = sum(1 for r in h1 if r["titulo"])
    print(
        f"\nGravado: h2_anuncios.jsonl ({len(h2)}), h1_reclamacoes.jsonl ({len(h1)}, "
        f"{with_title} com título), splits.json (H2 {len(splits['h2']['dev'])}/"
        f"{len(splits['h2']['test'])}, H1 {len(splits['h1']['dev'])}/{len(splits['h1']['test'])})"
    )
    print("OK: gabaritos conferidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
