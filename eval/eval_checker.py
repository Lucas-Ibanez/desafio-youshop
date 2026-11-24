"""Teste 1 do checador contra os 60 anúncios da H2 (T08, CONTEXTO 14).

Uso: uv run python tasks.py eval-checador   [--mudancas "o que mudou desde a última rodada"]

- Ficha genérica da categoria do gabarito (sem condições: o checador só extrai e registra).
- Duas configurações: só regras e regras + modelo (cache em disco; LLM_OFFLINE respeitado).
- Métricas por split (dev, test, total); o `test` é o principal (CONTEXTO 14.4).
- Grava eval/reports/checador_h2.md, checador_h2.json e erros_checador.csv.
- Rodada: v1 na primeira vez; quando regras, prompt ou modelo mudam, v2, v3... com o que mudou.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from metrics import cohen_kappa, confusion, precision_recall, wilson

from promessa.checker.llm_layer import PROMPT, run_layer2
from promessa.checker.segment import segment
from promessa.checker.service import generic_context, llm_enabled, run_layer1
from promessa.config import get_settings
from promessa.db.enums import Category
from promessa.llm.client import PROMPTS_DIR, LLMError
from promessa.rules.loader import RULES_DIR, load_rules

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"
REPORTS = ROOT / "eval" / "reports"
MD, JSON, CSV = (REPORTS / n for n in ("checador_h2.md", "checador_h2.json", "erros_checador.csv"))
EVIDENT = ["S06", "S22", "S25", "S26"]
SPLITS = ("dev", "test", "total")
CONFIGS = {"regras": "só regras", "regras+modelo": "regras + modelo"}
GOALS = {"sensibilidade": 1.0, "kappa": 0.6, "recall_verificavel": 0.8}
MANUAL_N, MANUAL_SEED = 10, 11
WORKERS = 4


@dataclass
class Prediction:
    overall: str
    findings: list[dict] = field(default_factory=list)
    error: str | None = None

    @property
    def flagged(self) -> bool:  # "indício" = bloquear ou revisar
        return self.overall in ("bloquear", "revisar")

    @property
    def extracted(self) -> list[dict]:
        return [f["extracted"] for f in self.findings if f.get("extracted")]


def _finding_dict(f) -> dict:
    return {
        "output": f.output.value,
        "rule_key": f.rule_key,
        "source": f.source.value,
        "reason_type": f.reason_type,
        "excerpt": f.excerpt,
        "extracted": f.extracted,
    }


def _overall(findings: list[dict]) -> str:
    order = {"bloquear": 3, "revisar": 2, "registrar": 1}
    return max((f["output"] for f in findings), key=order.get, default="limpo")


# --- Predição ----------------------------------------------------------------------------


def predict(rows: list[dict], with_model: bool) -> dict[str, Prediction]:
    rules = load_rules()
    contexts = {c: generic_context(Category(c), rules) for c in {r["categoria"] for r in rows}}
    layer1 = {}
    for r in rows:
        result = run_layer1(r["texto"], contexts[r["categoria"]], rules=rules)
        layer1[r["id"]] = (result.findings, [_finding_dict(f) for f in result.findings])
    if not with_model:
        return {i: Prediction(_overall(fs), fs) for i, (_, fs) in layer1.items()}

    model = get_settings().checker_model

    def run_one(r: dict) -> tuple[str, Prediction]:
        found, dicts = layer1[r["id"]]
        try:
            added = run_layer2(
                r["texto"], segment(r["texto"]), contexts[r["categoria"]], found, model
            )
        except LLMError as e:
            return r["id"], Prediction(_overall(dicts), dicts, error=str(e)[:200])
        all_findings = dicts + [_finding_dict(f) for f in added]
        return r["id"], Prediction(_overall(all_findings), all_findings)

    with ThreadPoolExecutor(WORKERS) as pool:
        return dict(pool.map(run_one, rows))


# --- Métricas ----------------------------------------------------------------------------


def metrics_for(rows: list[dict], preds: dict[str, Prediction]) -> dict:
    gold = [r["nao_conforme"] for r in rows]
    pred = [preds[r["id"]].flagged for r in rows]
    evident = [r for r in rows if r["irregular_evidente"]]
    verif = [r for r in rows if r["promessa_verificavel"]]
    hits_evident = sum(preds[r["id"]].overall == "bloquear" for r in evident)
    hits_verif = sum(bool(preds[r["id"]].extracted) for r in verif)
    precision, recall = precision_recall(gold, pred, True)
    return {
        "n": len(rows),
        "kappa": cohen_kappa(gold, pred),
        "acuracia": sum(g == p for g, p in zip(gold, pred, strict=True)) / len(rows)
        if rows
        else None,
        "precisao_indicio": precision,
        "recall_indicio": recall,
        "matriz": {
            str(k): {str(kk): v for kk, v in d.items()}
            for k, d in confusion(gold, pred, [True, False]).items()
        },
        "sensibilidade": {
            "acertos": hits_evident,
            "n": len(evident),
            "valor": hits_evident / len(evident) if evident else None,
        },
        "recall_verificavel": {
            "acertos": hits_verif,
            "n": len(verif),
            "valor": hits_verif / len(verif) if verif else None,
            "ic95": wilson(hits_verif, len(verif)),
        },
    }


def split_rows(rows: list[dict], splits: dict) -> dict[str, list[dict]]:
    by_id = {r["id"]: r for r in rows}
    return {
        "dev": [by_id[i] for i in splits["h2"]["dev"]],
        "test": [by_id[i] for i in splits["h2"]["test"]],
        "total": rows,
    }


# --- Versão da rodada --------------------------------------------------------------------


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def fingerprint(model: str | None) -> dict[str, str]:
    fp = {f"data/rules/{p.name}": _sha(p) for p in sorted(RULES_DIR.glob("*.yaml"))}
    fp[f"prompt {PROMPT}"] = _sha(PROMPTS_DIR / f"{PROMPT}.md")
    fp["modelo"] = model or "(sem modelo)"
    return fp


def next_run(history: list[dict], fp: dict[str, str], note: str | None) -> dict:
    if not history:
        return {"versao": "v1", "mudancas": note or "primeira rodada"}
    last = history[-1]
    if last["fingerprint"] == fp:
        return {"versao": last["versao"], "mudancas": last["mudancas"]}
    changed = sorted(
        k for k in fp.keys() | last["fingerprint"].keys() if fp.get(k) != last["fingerprint"].get(k)
    )
    text = "mudou: " + ", ".join(changed) + (f". {note}" if note else "")
    return {"versao": f"v{int(last['versao'][1:]) + 1}", "mudancas": text}


# --- Conferência manual ------------------------------------------------------------------


def old_marks() -> dict[str, str]:
    """Marcas que o Lucas já fez na conferência manual (sobrevivem a novas rodadas)."""
    if not MD.exists():
        return {}
    marks = {}
    section = MD.read_text(encoding="utf-8").split("## Conferência manual", 1)
    for line in section[1].splitlines() if len(section) == 2 else []:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.fullmatch(r"[A-Z]\d\d", cells[0]):
            marks[cells[0]] = cells[-1]
    return marks


def manual_sample(rows: list[dict], preds: dict[str, Prediction]) -> list[dict]:
    candidates = sorted(
        r["id"] for r in rows if r["promessa_verificavel"] and preds[r["id"]].extracted
    )
    chosen = sorted(random.Random(MANUAL_SEED).sample(candidates, min(MANUAL_N, len(candidates))))
    by_id = {r["id"]: r for r in rows}
    return [{"id": i, "texto": by_id[i]["texto"], "extraido": preds[i].extracted} for i in chosen]


# --- Relatório ---------------------------------------------------------------------------


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v:.0%}"


def _num(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}"


def _ok(value: float | None, goal: float) -> str:
    return "—" if value is None else ("✅" if value >= goal - 1e-9 else "❌")


def render_md(report: dict, rows: list[dict], splits: dict, preds_by_cfg, sample, marks) -> str:
    run = report["rodada"]
    lines = [
        "# Teste 1 do checador (H2, 60 anúncios)",
        "",
        f"- **Data:** {report['data']}",
        f"- **Rodada:** {run['versao']} ({run['mudancas']})",
        f"- **Regras:** {', '.join(report['versoes_regras'])}",
        f"- **Prompt:** `{PROMPT}` · **Modelo:** `{report['modelo'] or 'não rodou'}`",
        "- **Ficha:** genérica da categoria do gabarito (regras oficiais da categoria; condições da "
        "oferta não informadas, então condição anunciada é só extraída e registrada).",
        "- **Indício:** predição `bloquear` ou `revisar` × gabarito não conforme (indício + irregular evidente).",
        "",
        "## Vazamentos conhecidos (CONTEXTO 14.4)",
        "",
        "- As regras da camada 1 foram escritas a partir desta mesma auditoria H2: o resultado é **otimista**.",
        "- O prompt do checador não usa exemplos do gabarito; mesmo assim, a métrica principal é a do split `test`.",
        "- Depois da primeira rodada no `test`, toda mudança de regra ou prompt vira nova rodada (v2, v3...).",
        "",
    ]
    if report.get("avisos"):
        lines += ["## Avisos", ""] + [f"- {a}" for a in report["avisos"]] + [""]

    lines += [
        "## Metas do guia",
        "",
        "`test` é o split principal. ✅/❌ em cada coluna; nada é escondido.",
        "",
    ]
    lines += ["| Meta | Configuração | dev | test | total |", "|---|---|---|---|---|"]
    for cfg, label in CONFIGS.items():
        m = report["metricas"].get(cfg)
        if not m:
            lines.append(f"| (todas) | {label} | não rodou | não rodou | não rodou |")
            continue
        cells = {
            "sens": [
                f"{m[s]['sensibilidade']['acertos']}/{m[s]['sensibilidade']['n']} "
                f"{_ok(m[s]['sensibilidade']['valor'], GOALS['sensibilidade'])}"
                for s in SPLITS
            ],
            "kappa": [
                f"{_num(m[s]['kappa'])} {_ok(m[s]['kappa'], GOALS['kappa'])}" for s in SPLITS
            ],
            "recall": [
                f"{m[s]['recall_verificavel']['acertos']}/{m[s]['recall_verificavel']['n']} "
                f"({_pct(m[s]['recall_verificavel']['valor'])}) "
                f"{_ok(m[s]['recall_verificavel']['valor'], GOALS['recall_verificavel'])}"
                for s in SPLITS
            ],
        }
        lines.append(
            f"| Sensibilidade nas irregulares evidentes (`bloquear`), meta 4 de 4 | {label} | "
            + " | ".join(cells["sens"])
            + " |"
        )
        lines.append(
            f'| Kappa no binário "indício", meta ≥ 0,6 | {label} | '
            + " | ".join(cells["kappa"])
            + " |"
        )
        lines.append(
            f"| Recall de promessa verificável (peça), meta ≥ 80% | {label} | "
            + " | ".join(cells["recall"])
            + " |"
        )
    lines.append("")

    lines += [
        "## Outras métricas (total)",
        "",
        "| Configuração | acurácia | precisão do indício | recall do indício | IC95% do recall verificável |",
        "|---|---|---|---|---|",
    ]
    for cfg, label in CONFIGS.items():
        m = report["metricas"].get(cfg)
        if m:
            t = m["total"]
            ic = t["recall_verificavel"]["ic95"]
            lines.append(
                f"| {label} | {_pct(t['acuracia'])} | {_pct(t['precisao_indicio'])} | {_pct(t['recall_indicio'])} | "
                + (f"{ic[0]:.0%}–{ic[1]:.0%}" if ic else "—")
                + " |"
            )
    lines.append("")

    lines += [
        "## Irregulares evidentes (as 4 peças)",
        "",
        "| id | split | " + " | ".join(CONFIGS.values()) + " |",
        "|---|---|" + "---|" * len(CONFIGS),
    ]
    split_of = {i: s for s in ("dev", "test") for i in splits["h2"][s]}
    for i in EVIDENT:
        cells = []
        for cfg in CONFIGS:
            p = preds_by_cfg.get(cfg, {}).get(i)
            if p is None:
                cells.append("não rodou")
                continue
            keys = sorted({f["rule_key"] for f in p.findings if f["output"] == "bloquear"})
            cells.append(
                f"{p.overall} {'✅' if p.overall == 'bloquear' else '❌'}"
                + (f" ({', '.join(keys)})" if keys else "")
            )
        lines.append(f"| {i} | {split_of.get(i)} | " + " | ".join(cells) + " |")
    lines.append("")

    lines += ["## Matriz de confusão do indício (total)", ""]
    for cfg, label in CONFIGS.items():
        m = report["metricas"].get(cfg)
        if m:
            mx = m["total"]["matriz"]
            lines += [
                f"**{label}**",
                "",
                "| gabarito \\ predito | indício | sem indício |",
                "|---|---|---|",
                f"| não conforme | {mx['True']['True']} | {mx['True']['False']} |",
                f"| conforme | {mx['False']['True']} | {mx['False']['False']} |",
                "",
            ]

    lines += [
        "## Conferência manual (10 extrações sorteadas)",
        "",
        f"Semente {MANUAL_SEED}, entre as peças verificáveis com alguma promessa extraída "
        f"({report['config_conferencia']}). Lucas: marque a última coluna com `certo` ou `errado`; "
        "as marcas são mantidas nas próximas rodadas.",
        "",
        "| id | trecho do anúncio | extraído | certo ou errado |",
        "|---|---|---|---|",
    ]
    for item in sample:
        extracted = "; ".join(
            f"{e['attribute']}={e['value']}" + (f" {e['unit']}" if e.get("unit") else "")
            for e in item["extraido"]
        )
        text = item["texto"].replace("|", "/")
        lines.append(f"| {item['id']} | {text} | {extracted} | {marks.get(item['id'], '')} |")
    lines.append("")

    lines += [
        "## Erros",
        "",
        f"Detalhe por peça em `eval/reports/{CSV.name}` (fora do git). Resumo (total):",
        "",
    ]
    for cfg, label in CONFIGS.items():
        m = report["metricas"].get(cfg)
        if m:
            mx = m["total"]["matriz"]
            lines.append(
                f"- {label}: {mx['True']['False']} não conformes sem indício (falso negativo), "
                f"{mx['False']['True']} conformes com indício (falso positivo)."
            )
    lines.append("")

    lines += [
        "## Histórico de rodadas",
        "",
        "| rodada | data | o que mudou | kappa test (regras) | kappa test (regras+modelo) |",
        "|---|---|---|---|---|",
    ]
    for h in report["historico"]:
        lines.append(
            f"| {h['versao']} | {h['data']} | {h['mudancas']} | {_num(h['kappa_test'].get('regras'))} | {_num(h['kappa_test'].get('regras+modelo'))} |"
        )
    return "\n".join(lines) + "\n"


def write_errors(
    rows: list[dict], splits: dict, preds_by_cfg: dict[str, dict[str, Prediction]]
) -> int:
    split_of = {i: s for s in ("dev", "test") for i in splits["h2"][s]}
    out = []
    for cfg, preds in preds_by_cfg.items():
        for r in rows:
            p = preds[r["id"]]
            wrong = p.flagged != r["nao_conforme"] or (
                r["irregular_evidente"] and p.overall != "bloquear"
            )
            if wrong or p.error:
                out.append(
                    {
                        "id": r["id"],
                        "split": split_of.get(r["id"]),
                        "config": cfg,
                        "familia": r["familia"],
                        "categoria": r["categoria"],
                        "gold_veredito": r["veredito"],
                        "gold_nao_conforme": r["nao_conforme"],
                        "predito": p.overall,
                        "regras": " ".join(sorted({f["rule_key"] or "-" for f in p.findings})),
                        "trechos": " | ".join(f["excerpt"] for f in p.findings),
                        "erro_modelo": p.error or "",
                        "texto": r["texto"],
                    }
                )
    REPORTS.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "split",
        "config",
        "familia",
        "categoria",
        "gold_veredito",
        "gold_nao_conforme",
        "predito",
        "regras",
        "trechos",
        "erro_modelo",
        "texto",
    ]
    with CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    return len(out)


# --- Principal ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Teste 1 do checador (H2)")
    parser.add_argument("--mudancas", default=None, help="o que mudou desde a última rodada")
    parser.add_argument(
        "--sem-modelo", action="store_true", help="roda só a configuração de regras"
    )
    args = parser.parse_args(argv)

    with (GOLD / "h2_anuncios.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    splits = json.loads((GOLD / "splits.json").read_text(encoding="utf-8"))
    parts = split_rows(rows, splits)
    settings = get_settings()

    preds_by_cfg: dict[str, dict[str, Prediction]] = {"regras": predict(rows, with_model=False)}
    warnings_: list[str] = []
    model = None
    if not args.sem_modelo and llm_enabled():
        model = settings.checker_model
        preds_by_cfg["regras+modelo"] = predict(rows, with_model=True)
        failed = sorted(i for i, p in preds_by_cfg["regras+modelo"].items() if p.error)
        if failed:
            warnings_.append(
                f"O modelo falhou em {len(failed)} peça(s) ({', '.join(failed)}); nelas vale só a camada 1."
            )
    else:
        warnings_.append(
            "Configuração regras + modelo não rodou (modelo desligado, sem chave ou --sem-modelo)."
        )

    metrics = {
        cfg: {s: metrics_for(parts[s], preds) for s in SPLITS}
        for cfg, preds in preds_by_cfg.items()
    }
    previous = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    history = previous.get("historico", [])
    fp = fingerprint(model)
    run = next_run(history, fp, args.mudancas)
    now = datetime.now(UTC).astimezone().strftime("%d/%m/%Y %H:%M")
    entry = {
        **run,
        "data": now,
        "fingerprint": fp,
        "kappa_test": {cfg: m["test"]["kappa"] for cfg, m in metrics.items()},
    }
    history = [h for h in history if h["versao"] != run["versao"]] + [entry]

    cfg_sample = "regras+modelo" if "regras+modelo" in preds_by_cfg else "regras"
    sample = manual_sample(rows, preds_by_cfg[cfg_sample])
    rules = load_rules()
    report = {
        "data": now,
        "rodada": run,
        "modelo": model,
        "prompt": PROMPT,
        "versoes_regras": [f"{fid}.yaml@{f.versao}" for fid, f in rules.files.items()],
        "metricas": metrics,
        "metas": GOALS,
        "avisos": warnings_,
        "config_conferencia": CONFIGS[cfg_sample],
        "conferencia_manual": sample,
        "predicoes": {
            cfg: {
                i: {"overall": p.overall, "findings": p.findings, "erro": p.error}
                for i, p in preds.items()
            }
            for cfg, preds in preds_by_cfg.items()
        },
        "historico": history,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    marks = old_marks()
    JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    MD.write_text(
        render_md(report, rows, splits, preds_by_cfg, sample, marks), encoding="utf-8", newline="\n"
    )
    n_errors = write_errors(rows, splits, preds_by_cfg)

    print(f"Rodada {run['versao']} ({run['mudancas']})")
    for cfg, m in metrics.items():
        t = m["test"]
        print(
            f"  {CONFIGS[cfg]:<16} test: kappa={_num(t['kappa'])}  "
            f"evidentes={m['total']['sensibilidade']['acertos']}/4  "
            f"verificável={_pct(t['recall_verificavel']['valor'])}"
        )
    for w in warnings_:
        print(f"  AVISO: {w}")
    print(f"Relatório: {_rel(MD)} · erros: {n_errors} linhas em {_rel(CSV)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
