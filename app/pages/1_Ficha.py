"""Página 1 · Ficha de promessas (marca): versões, condições, regras com fonte e nova versão."""

import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from painel_comum import domain_error, product_name, product_select, sidebar  # noqa: E402
from ui.components import ident, page_header  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

from promessa.db.session import session_scope  # noqa: E402
from promessa.display import ACCESS_TYPE, RECURRENCE, label, money, num  # noqa: E402
from promessa.errors import DomainError  # noqa: E402
from promessa.facts import service as facts_service  # noqa: E402

apply_theme("Ficha do produto")
ctx = sidebar()
head = st.container()

product_id = product_select()
with session_scope() as session:
    versions = facts_service.list_versions(session, product_id)
numbers = [v.version for v in versions]
version = st.selectbox(
    "Versão",
    numbers,
    index=len(numbers) - 1,
    format_func=lambda n: (
        f"v{n} (vale desde {versions[n - 1].valid_from:%d/%m/%Y %H:%M}, por {versions[n - 1].created_by})"
    ),
    key="versao_ficha",
)
with session_scope() as session:
    facts = facts_service.get_product_facts(session, product_id, version)
page_header(
    "Ficha do produto",
    "O que este produto pode prometer, com a fonte de cada regra.",
    f"{escape(product_name(product_id))}, ficha {ident(f'v{facts.version}')}",
    container=head,
)

left, right = st.columns(2)
with left:
    st.subheader("Condições da oferta")
    st.table(
        pd.DataFrame(
            {
                "condição": [
                    "garantia",
                    "acesso",
                    "meses de acesso",
                    "cobrança",
                    "renovação automática",
                    "bônus",
                    "custos extras",
                ],
                "valor": [
                    f"{facts.guarantee_days} dias",
                    label(ACCESS_TYPE, facts.access_type),
                    facts.access_months or "—",
                    label(RECURRENCE, facts.recurrence),
                    "sim" if facts.auto_renewal else "não",
                    ", ".join(facts.bonuses) or "nenhum",
                    ", ".join(
                        f"{c['descricao']} ({money(c['valor_mensal_cents'])}/mês)"
                        for c in facts.extra_costs
                    )
                    or "nenhum",
                ],
            }
        ).astype(str)
    )
with right:
    st.subheader("Briefing para o creator")
    st.text(facts.briefing)

st.subheader(f"Regras desta versão ({len(facts.rules)})")
if facts.rules:
    st.dataframe(
        pd.DataFrame([r.model_dump(mode="json") for r in facts.rules])[
            ["rule_key", "kind", "tema", "output", "source", "reference", "text"]
        ],
        hide_index=True,
        width="stretch",
    )
else:
    st.write(
        "Nenhuma lista oficial para esta categoria; valem só as condições da oferta e os padrões gerais."
    )

st.divider()
st.subheader("Nova versão da ficha")
if ctx["role"] != "marca":
    st.info("Só a marca cria versões da ficha. Troque o papel para **Marca** na barra lateral.")
else:
    st.caption(
        "A versão atual não muda: a nova versão passa a valer a partir de agora (CDC art. 30: a oferta vincula)."
    )
    with st.form("nova_versao"):
        c1, c2, c3 = st.columns(3)
        guarantee = c1.number_input(
            "Garantia (dias)", min_value=0, value=int(facts.guarantee_days), step=1
        )
        access_types = ["vitalicio", "prazo", "assinatura", "nao_aplica"]
        access = c2.selectbox(
            "Acesso",
            access_types,
            index=access_types.index(facts.access_type.value),
            format_func=lambda v: label(ACCESS_TYPE, v),
        )
        months = c3.number_input(
            "Meses de acesso (só para prazo)",
            min_value=0,
            value=int(facts.access_months or 0),
            step=1,
        )
        recurrences = ["unica", "mensal", "anual"]
        recurrence = c1.selectbox(
            "Cobrança",
            recurrences,
            index=recurrences.index(facts.recurrence.value),
            format_func=lambda v: label(RECURRENCE, v),
        )
        renewal = c2.checkbox("Renovação automática", value=facts.auto_renewal)
        bonuses = c3.text_input("Bônus (separados por vírgula)", value=", ".join(facts.bonuses))
        costs = st.text_area(
            "Custos extras (um por linha: descrição; valor mensal em reais)",
            value="\n".join(
                f"{c['descricao']}; {num(c['valor_mensal_cents'] / 100)}" for c in facts.extra_costs
            ),
        )
        brand_rule = st.text_input("Frase que a marca proíbe (opcional)")
        submitted = st.form_submit_button("Criar nova versão")
    if submitted:
        extra = []
        for line in costs.splitlines():
            if line.strip():
                desc, _, value = line.partition(";")
                try:
                    extra.append(
                        {
                            "descricao": desc.strip(),
                            "valor_mensal_cents": round(float(value.replace(",", ".")) * 100),
                        }
                    )
                except ValueError:
                    st.error(f"Valor inválido em custos extras: {line!r}")
                    st.stop()
        data = {
            "guarantee_days": int(guarantee),
            "access_type": access,
            "access_months": int(months) if access == "prazo" else None,
            "recurrence": recurrence,
            "auto_renewal": renewal,
            "bonuses": [b.strip() for b in bonuses.split(",") if b.strip()],
            "extra_costs": extra,
            "brand_rules": [{"kind": "proibida", "text": brand_rule}] if brand_rule.strip() else [],
        }
        try:
            with session_scope() as session:
                result = facts_service.create_facts_version(
                    session, product_id, data, ctx["reviewer"] or "marca"
                )
        except DomainError as e:
            domain_error(e)
        else:
            st.success(
                f"Versão {result.version} criada. A versão {result.version - 1} continua guardada."
            )
            for w in result.warnings:
                st.warning(f"{w.rule_key}: {w.message}")
