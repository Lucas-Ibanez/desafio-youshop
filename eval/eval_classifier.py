"""Teste 1 do classificador contra os 172 compradores da H1 (T12, CONTEXTO 14).

Uso: uv run python tasks.py eval-classificador   [--com-titulos] [--mudancas "..."]

- `classify_text` (sem banco) com texto = resumo em paráfrase; com `--com-titulos`, também só
  com o título da reclamação (palavras do comprador; CONTEXTO 14.4).
- Métricas por split (dev, test, total); o `test` é o principal.
- Grava eval/reports/classificador_h1.md, classificador_h1.json e erros_classificador.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from common import next_run, num, ok, pct, rel, sha
from metrics import accuracy, cohen_kappa, confusion, precision_recall

from promessa.config import get_settings
from promessa.llm.client import PROMPTS_DIR
from promessa.refunds.classifier import PROMPT, classify_text, llm_available, prompt_examples
from promessa.rules.loader import RULES_DIR

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"
REPORTS = ROOT / "eval" / "reports"
MD, JSON, CSV = (
    REPORTS / n for n in ("classificador_h1.md", "classificador_h1.json", "erros_classificador.csv")
)
SPLITS = ("dev", "test", "total")
MAIN = ["promessa", "acesso", "processo", "fraude", "outros"]
SUBTYPES = [
    "diferente_do_anunciado",
    "condicao_da_oferta",
    "informacao_omitida",
    "resultado_prometido",
    "expectativa",
]
GOALS = {"acuracia": 0.8, "kappa": 0.6, "subtipo": 0.7}
CUT_CLASSES = ("promessa", "acesso", "processo")  # critério de corte do guia
CONFIGS = {"parafrase": "resumo em paráfrase", "titulo": "só o título"}
WORKERS = 4


def subtype(cause: str, subcause: str) -> str:
    if cause == "promessa_explicita":
        return subcause
    if cause == "promessa_expectativa":
        return "expectativa"
    return "nao_promessa"


# --- Predição ----------------------------------------------------------------------------


def predict(rows: list[dict], field: str) -> dict[str, dict]:
    def one(r: dict) -> tuple[str, dict]:
        text = r.get(field) or ""
        c = classify_text(text, r.get("categoria_produto") or r.get("tipo_produto"))
        return r["id"], {
            "cause": c.cause,
            "subcause": c.subcause,
            "main_cause": c.main_cause,
            "confidence": c.confidence,
            "explanation": c.explanation,
            "source": c.source,
            "buyer_belief": c.buyer_belief.model_dump() if c.buyer_belief else None,
        }

    with ThreadPoolExecutor(WORKERS) as pool:
        return dict(pool.map(one, rows))


# --- Métricas ----------------------------------------------------------------------------


def metrics_for(rows: list[dict], preds: dict[str, dict]) -> dict:
    gold = [r["causa_principal"] for r in rows]
    pred = [preds[r["id"]]["main_cause"] for r in rows]
    promise = [r for r in rows if r["causa_principal"] == "promessa"]
    sub_gold = [subtype(r["causa"], r["subcausa"]) for r in promise]
    sub_pred = [subtype(preds[r["id"]]["cause"], preds[r["id"]]["subcause"]) for r in promise]
    explicit_gold = [r["causa"] == "promessa_explicita" for r in rows]
    explicit_pred = [preds[r["id"]]["cause"] == "promessa_explicita" for r in rows]
    p_exp, r_exp = precision_recall(explicit_gold, explicit_pred, True)
    cut = [(g, p) for g, p in zip(gold, pred, strict=True) if g in CUT_CLASSES]
    cut_gold, cut_pred = [g for g, _ in cut], [p for _, p in cut]
    return {
        "n": len(rows),
        "acuracia": accuracy(gold, pred),
        "kappa": cohen_kappa(gold, pred),
        "matriz": confusion(gold, pred, MAIN),
        "subtipo": {"n": len(promise), "acuracia": accuracy(sub_gold, sub_pred)},
        "promessa_explicita": {
            "precisao": p_exp,
            "recall": r_exp,
            "n_gold": sum(explicit_gold),
            "n_pred": sum(explicit_pred),
        },
        "corte": {
            "n": len(cut),
            "acuracia": accuracy(cut_gold, cut_pred),
            "kappa": cohen_kappa(cut_gold, cut_pred),
        },
        "sem_modelo": sum(preds[r["id"]]["source"] == "sem_modelo" for r in rows),
    }


def fingerprint(model: str) -> dict[str, str]:
    return {
        "data/rules/taxonomia_devolucao.yaml": sha(RULES_DIR / "taxonomia_devolucao.yaml"),
        f"prompt {PROMPT}": sha(PROMPTS_DIR / f"{PROMPT}.md"),
        "exemplos": ",".join(r["id"] for r in prompt_examples()),
        "modelo": model,
    }


# --- Relatório ---------------------------------------------------------------------------


def _matrix_md(matrix: dict, labels: list[str]) -> list[str]:
    lines = [
        "| gabarito \\ predito | " + " | ".join(labels) + " | total |",
        "|---|" + "---|" * (len(labels) + 1),
    ]
    for g in labels:
        row = [matrix[g][p] for p in labels]
        cells = [f"**{v}**" if g == p else str(v) for p, v in zip(labels, row, strict=True)]
        lines.append(f"| {g} | " + " | ".join(cells) + f" | {sum(row)} |")
    return lines


def cut_verdict(m: dict) -> tuple[str, str]:
    c = m["corte"]
    yes = (c["acuracia"] or 0) >= GOALS["acuracia"] and (c["kappa"] or 0) >= GOALS["kappa"]
    text = (
        f"Nas {c['n']} reclamações do `test` cujo gabarito é promessa, acesso ou processo, o classificador "
        f"acertou {pct(c['acuracia'])} (meta ≥ 80%) com kappa {num(c['kappa'])} (meta ≥ 0,6)."
    )
    return ("sim" if yes else "não"), text


def render_md(report: dict) -> str:
    run = report["rodada"]
    lines = [
        "# Teste 1 do classificador (H1, 172 compradores)",
        "",
        f"- **Data:** {report['data']}",
        f"- **Rodada:** {run['versao']} ({run['mudancas']})",
        f"- **Prompt:** `{PROMPT}` · **Modelo:** `{report['modelo']}`",
        f"- **Exemplos no prompt (só do split dev):** {', '.join(report['exemplos'])}",
        '- **Texto classificado:** resumo em paráfrase (coluna "Resumo" da H1)'
        + (
            "; segunda rodada só com o título da reclamação."
            if "titulo" in report["metricas"]
            else "."
        ),
        "",
        "## Vazamentos conhecidos (CONTEXTO 14.4)",
        "",
        "- O texto da H1 é uma **paráfrase escrita por quem codificou**: pode carregar a categoria nas palavras. "
        "O resultado com paráfrase tende a ser otimista.",
        "- Os 8 exemplos do prompt vêm só do split `dev`; a métrica principal é a do `test`.",
        "- Depois da primeira rodada no `test`, mudança de prompt, exemplos ou taxonomia vira nova rodada.",
        "- A rodada só com o título usa as palavras do comprador (slug do Reclame Aqui) e serve de contraprova"
        + (
            " (rodou nesta versão)."
            if "titulo" in report["metricas"]
            else " (não rodou nesta versão; use `--com-titulos`)."
        ),
        "",
    ]
    if report.get("avisos"):
        lines += ["## Avisos", ""] + [f"- {a}" for a in report["avisos"]] + [""]

    verdict, text = cut_verdict(report["metricas"]["parafrase"]["test"])
    lines += [
        "## Critério de corte do guia",
        "",
        f"**O classificador separa promessa de acesso e processo com acerto aceitável? {verdict.upper()}.** {text}",
        "",
    ]

    lines += [
        "## Metas do guia",
        "",
        "`test` é o split principal. ✅/❌ em cada coluna; nada é escondido.",
        "",
        "| Meta | Texto | dev | test | total |",
        "|---|---|---|---|---|",
    ]
    for cfg, m in report["metricas"].items():
        label = CONFIGS[cfg]
        lines.append(
            f"| Acurácia na causa principal, meta ≥ 80% | {label} | "
            + " | ".join(
                f"{pct(m[s]['acuracia'])} {ok(m[s]['acuracia'], GOALS['acuracia'])}" for s in SPLITS
            )
            + " |"
        )
        lines.append(
            f"| Kappa na causa principal, meta ≥ 0,6 | {label} | "
            + " | ".join(
                f"{num(m[s]['kappa'])} {ok(m[s]['kappa'], GOALS['kappa'])}" for s in SPLITS
            )
            + " |"
        )
        lines.append(
            f"| Acurácia do subtipo nas reclamações de promessa, meta ≥ 70% | {label} | "
            + " | ".join(
                f"{pct(m[s]['subtipo']['acuracia'])} ({m[s]['subtipo']['n']}) {ok(m[s]['subtipo']['acuracia'], GOALS['subtipo'])}"
                for s in SPLITS
            )
            + " |"
        )
    lines.append("")

    lines += [
        "## Promessa explícita (é o que pesa no creator: precisão importa mais)",
        "",
        "| Texto | split | precisão | recall | gabarito | predito |",
        "|---|---|---|---|---|---|",
    ]
    for cfg, m in report["metricas"].items():
        for s in SPLITS:
            e = m[s]["promessa_explicita"]
            lines.append(
                f"| {CONFIGS[cfg]} | {s} | {pct(e['precisao'])} | {pct(e['recall'])} | {e['n_gold']} | {e['n_pred']} |"
            )
    lines.append("")

    for cfg, m in report["metricas"].items():
        lines += [
            f"## Matriz de confusão da causa principal ({CONFIGS[cfg]}, test)",
            "",
            "Diagonal em negrito = acerto.",
            "",
        ]
        lines += _matrix_md(m["test"]["matriz"], MAIN) + [""]
        lines += ["Total (dev + test):", ""] + _matrix_md(m["total"]["matriz"], MAIN) + [""]

    lines += [
        "## Erros",
        "",
        f"Detalhe por reclamação em `eval/reports/{CSV.name}` (fora do git).",
        "",
    ]
    for cfg, m in report["metricas"].items():
        t = m["total"]
        wrong = t["n"] - round((t["acuracia"] or 0) * t["n"])
        lines.append(
            f"- {CONFIGS[cfg]}: {wrong} de {t['n']} com causa principal diferente do gabarito."
        )
    lines.append("")
    lines += [
        "## Histórico de rodadas",
        "",
        "| rodada | data | o que mudou | acurácia test | kappa test |",
        "|---|---|---|---|---|",
    ]
    for h in report["historico"]:
        lines.append(
            f"| {h['versao']} | {h['data']} | {h['mudancas']} | {pct(h['acuracia_test'])} | {num(h['kappa_test'])} |"
        )
    return "\n".join(lines) + "\n"


def write_errors(rows: list[dict], splits: dict, preds_by_cfg: dict[str, dict]) -> int:
    split_of = {i: s for s in ("dev", "test") for i in splits["h1"][s]}
    out = []
    for cfg, preds in preds_by_cfg.items():
        for r in rows:
            p = preds[r["id"]]
            if (
                p["main_cause"] != r["causa_principal"]
                or (r["causa_principal"] == "promessa" and p["cause"] != r["causa"])
                or subtype(p["cause"], p["subcause"]) != subtype(r["causa"], r["subcausa"])
            ):
                out.append(
                    {
                        "id": r["id"],
                        "split": split_of.get(r["id"]),
                        "config": cfg,
                        "gold": f"{r['causa']}/{r['subcausa']}",
                        "predito": f"{p['cause']}/{p['subcause']}",
                        "confianca": p["confidence"],
                        "explicacao": p["explanation"],
                        "texto": r["texto"] if cfg == "parafrase" else r.get("titulo"),
                    }
                )
    REPORTS.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "split",
                "config",
                "gold",
                "predito",
                "confianca",
                "explicacao",
                "texto",
            ],
        )
        writer.writeheader()
        writer.writerows(out)
    return len(out)


# --- Principal ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Teste 1 do classificador (H1)")
    parser.add_argument("--com-titulos", action="store_true", help="roda também só com o título")
    parser.add_argument("--mudancas", default=None, help="o que mudou desde a última rodada")
    args = parser.parse_args(argv)

    if not llm_available():
        print(
            "O classificador precisa do modelo (GEMINI_API_KEY ou LLM_OFFLINE=true com cache). Nada foi gravado."
        )
        return 1
    with (GOLD / "h1_reclamacoes.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    splits = json.loads((GOLD / "splits.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    parts = {
        "dev": [by_id[i] for i in splits["h1"]["dev"]],
        "test": [by_id[i] for i in splits["h1"]["test"]],
        "total": rows,
    }

    preds_by_cfg = {"parafrase": predict(rows, "texto")}
    if args.com_titulos:
        preds_by_cfg["titulo"] = predict(rows, "titulo")
    metrics = {
        cfg: {s: metrics_for(parts[s], preds) for s in SPLITS}
        for cfg, preds in preds_by_cfg.items()
    }
    warnings_ = []
    for cfg, m in metrics.items():
        if m["total"]["sem_modelo"]:
            warnings_.append(
                f"{CONFIGS[cfg]}: o modelo não respondeu em {m['total']['sem_modelo']} reclamação(ões); "
                "nelas a predição ficou `outros` (conta como erro)."
            )

    model = get_settings().classifier_model
    previous = json.loads(JSON.read_text(encoding="utf-8")) if JSON.exists() else {}
    history = previous.get("historico", [])
    fp = fingerprint(model)
    run = next_run(history, fp, args.mudancas)
    now = datetime.now(UTC).astimezone().strftime("%d/%m/%Y %H:%M")
    test = metrics["parafrase"]["test"]
    entry = {
        **run,
        "data": now,
        "fingerprint": fp,
        "acuracia_test": test["acuracia"],
        "kappa_test": test["kappa"],
    }
    history = [h for h in history if h["versao"] != run["versao"]] + [entry]

    def jsonable(m):  # chaves da matriz como texto
        return json.loads(json.dumps(m, default=str))

    report = {
        "data": now,
        "rodada": run,
        "modelo": model,
        "prompt": PROMPT,
        "exemplos": [r["id"] for r in prompt_examples()],
        "metas": GOALS,
        "avisos": warnings_,
        "metricas": jsonable(metrics),
        "predicoes": preds_by_cfg,
        "historico": history,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    MD.write_text(render_md(report), encoding="utf-8", newline="\n")
    n_errors = write_errors(rows, splits, preds_by_cfg)

    verdict, _ = cut_verdict(report["metricas"]["parafrase"]["test"])
    print(f"Rodada {run['versao']} ({run['mudancas']})")
    for cfg, m in metrics.items():
        t = m["test"]
        print(
            f"  {CONFIGS[cfg]:<22} test: acurácia={pct(t['acuracia'])} kappa={num(t['kappa'])} "
            f"subtipo={pct(t['subtipo']['acuracia'])} precisão explícita={pct(t['promessa_explicita']['precisao'])}"
        )
    print(f"  Critério de corte (promessa × acesso × processo): {verdict}")
    for w in warnings_:
        print(f"  AVISO: {w}")
    print(f"Relatório: {rel(MD)} · erros: {n_errors} linhas em {rel(CSV)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
