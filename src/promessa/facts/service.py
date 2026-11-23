"""Ficha de promessas (módulo 1): versões, regras materializadas e briefing (CONTEXTO 8, 9, 10).

A ficha é imutável: cada mudança cria uma versão nova (trigger no banco). Na criação, as regras
oficiais da categoria são copiadas para `claim_rule` (D4), junto com as regras da marca.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from promessa.db.enums import AccessType, Category, Recurrence, RuleKind, RuleOutput, RuleSource
from promessa.db.models import ClaimRule, Product, ProductFacts, get_current_facts, utcnow
from promessa.errors import (
    FICHA_INEXISTENTE,
    FICHA_INVALIDA,
    PRODUTO_INEXISTENTE,
    DomainError,
)
from promessa.rules.loader import RuleSet, load_rules
from promessa.rules.match import find_hits
from promessa.rules.normalize import normalize
from promessa.rules.schema import In28File

BRIEFING_MAX_WORDS = 150
BRAND_REFERENCE = "ficha da marca"

# --- Entrada -----------------------------------------------------------------------------

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExtraCost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descricao: Text
    valor_mensal_cents: int = Field(ge=0)


class BrandRule(BaseModel):
    """Regra declarada pela marca. Sem `termos`, o próprio texto vira o termo a procurar."""

    model_config = ConfigDict(extra="forbid")

    kind: RuleKind
    text: Text
    rule_key: str | None = Field(default=None, pattern=r"^MARCA-[A-Z0-9-]+$")
    termos: list[str] = Field(default_factory=list)
    output: RuleOutput | None = None  # só proibidas; padrão bloquear


class FactsInput(BaseModel):
    """Condições da oferta de uma nova versão da ficha."""

    model_config = ConfigDict(extra="forbid")

    guarantee_days: int
    access_type: AccessType
    access_months: int | None = None
    recurrence: Recurrence
    auto_renewal: bool = False
    bonuses: list[Text] = Field(default_factory=list)
    extra_costs: list[ExtraCost] = Field(default_factory=list)
    valid_from: datetime | None = None
    brand_rules: list[BrandRule] = Field(default_factory=list)


# --- Saída -------------------------------------------------------------------------------


class RuleView(BaseModel):
    rule_key: str
    kind: RuleKind
    tema: str | None
    text: str
    source: RuleSource
    reference: str
    output: RuleOutput | None


class FactsView(BaseModel):
    product_id: str
    product_name: str
    category: Category
    version: int
    guarantee_days: int
    access_type: AccessType
    access_months: int | None
    recurrence: Recurrence
    auto_renewal: bool
    bonuses: list[str]
    extra_costs: list[dict[str, Any]]
    valid_from: datetime
    created_by: str
    rules: list[RuleView]
    briefing: str


class NameWarning(BaseModel):
    rule_key: str
    excerpt: str
    message: str


class UpsertResult(BaseModel):
    product_id: str
    version: int
    warnings: list[NameWarning]


# --- Validação ---------------------------------------------------------------------------


def _invalid(message: str) -> DomainError:
    return DomainError(FICHA_INVALIDA, message)


def validate_facts(data: FactsInput | dict[str, Any]) -> FactsInput:
    """Valida as condições. Erro vira `FICHA_INVALIDA` com explicação em português."""
    if isinstance(data, dict):
        try:
            data = FactsInput.model_validate(data)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()
            )
            raise _invalid(f"Dados da ficha inválidos ({problems}).") from e
    if data.guarantee_days < 7:
        raise _invalid(
            f"A garantia precisa ser de pelo menos 7 dias (CDC art. 49, direito de "
            f"arrependimento). Recebido: {data.guarantee_days} dias."
        )
    if data.access_type == AccessType.PRAZO and not data.access_months:
        raise _invalid("Acesso por prazo precisa dizer quantos meses (`access_months`).")
    if data.access_type != AccessType.PRAZO and data.access_months is not None:
        raise _invalid("`access_months` só vale para acesso por prazo.")
    if data.access_months is not None and data.access_months <= 0:
        raise _invalid("`access_months` precisa ser maior que zero.")
    if data.auto_renewal and data.recurrence == Recurrence.UNICA:
        raise _invalid("Renovação automática não combina com pagamento único.")
    keys = [r.rule_key for r in data.brand_rules if r.rule_key]
    if len(keys) != len(set(keys)):
        raise _invalid("Há `rule_key` repetido nas regras da marca.")
    if any(r.kind == RuleKind.PERMITIDA and r.output for r in data.brand_rules):
        raise _invalid("Regra permitida não tem `output`; só a proibida (bloquear ou revisar).")
    return data


# --- Consultas ---------------------------------------------------------------------------


def get_product(session: Session, product_id: str) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise DomainError(PRODUTO_INEXISTENTE, f"O produto {product_id!r} não existe.")
    return product


def get_facts(session: Session, product_id: str, version: int | None = None) -> ProductFacts:
    """Versão pedida da ficha, ou a vigente agora quando `version` é None."""
    get_product(session, product_id)
    if version is None:
        facts = get_current_facts(session, product_id)
        if facts is None:
            raise DomainError(FICHA_INEXISTENTE, f"O produto {product_id!r} ainda não tem ficha.")
        return facts
    facts = session.scalars(
        select(ProductFacts).where(
            ProductFacts.product_id == product_id, ProductFacts.version == version
        )
    ).first()
    if facts is None:
        raise DomainError(
            FICHA_INEXISTENTE, f"A versão {version} da ficha de {product_id!r} não existe."
        )
    return facts


def get_rules(session: Session, facts: ProductFacts) -> list[ClaimRule]:
    return list(
        session.scalars(
            select(ClaimRule).where(ClaimRule.facts_id == facts.id).order_by(ClaimRule.id)
        )
    )


def get_product_facts(session: Session, product_id: str, version: int | None = None) -> FactsView:
    """Ficha (condições), regras com fonte e briefing. Base da ferramenta `get_product_facts`."""
    product = get_product(session, product_id)
    facts = get_facts(session, product_id, version)
    rules = get_rules(session, facts)
    return FactsView(
        product_id=product.id,
        product_name=product.name,
        category=product.category,
        version=facts.version,
        guarantee_days=facts.guarantee_days,
        access_type=facts.access_type,
        access_months=facts.access_months,
        recurrence=facts.recurrence,
        auto_renewal=facts.auto_renewal,
        bonuses=list(facts.bonuses),
        extra_costs=list(facts.extra_costs),
        valid_from=facts.valid_from,
        created_by=facts.created_by,
        rules=[_rule_view(r) for r in rules],
        briefing=build_briefing(facts, product, rules),
    )


def _rule_view(rule: ClaimRule) -> RuleView:
    return RuleView(
        rule_key=rule.rule_key,
        kind=rule.kind,
        tema=(rule.payload or {}).get("tema"),
        text=rule.text,
        source=rule.source,
        reference=rule.reference,
        output=rule.output,
    )


# --- Criação de versão -------------------------------------------------------------------


def create_facts_version(
    session: Session,
    product_id: str,
    data: FactsInput | dict[str, Any],
    created_by: str,
    rules: RuleSet | None = None,
) -> UpsertResult:
    """Cria a próxima versão da ficha, materializa as regras e avisa sobre o nome do produto."""
    product = get_product(session, product_id)
    data = validate_facts(data)
    rules = rules or load_rules()

    last = session.scalar(
        select(func.max(ProductFacts.version)).where(ProductFacts.product_id == product_id)
    )
    valid_from = _as_utc(data.valid_from) if data.valid_from else utcnow()
    if last is not None:
        previous = get_facts(session, product_id, last)
        if valid_from < previous.valid_from:
            raise _invalid(
                f"A nova versão precisa valer a partir de {previous.valid_from:%d/%m/%Y %H:%M} "
                f"(início da versão {last}) ou depois."
            )
    facts = ProductFacts(
        product_id=product_id,
        version=(last or 0) + 1,
        guarantee_days=data.guarantee_days,
        access_type=data.access_type,
        access_months=data.access_months,
        recurrence=data.recurrence,
        auto_renewal=data.auto_renewal,
        bonuses=list(data.bonuses),
        extra_costs=[c.model_dump() for c in data.extra_costs],
        valid_from=valid_from,
        created_by=created_by,
    )
    session.add(facts)
    session.flush()

    claim_rules = _official_rules(rules, product.category) + _brand_rules(data.brand_rules)
    for rule in claim_rules:
        rule.facts_id = facts.id
    session.add_all(claim_rules)
    session.flush()

    warnings = name_warnings(product.name, product.category, rules, claim_rules)
    return UpsertResult(product_id=product_id, version=facts.version, warnings=warnings)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _official_rules(rules: RuleSet, category: Category) -> list[ClaimRule]:
    """Cópia das regras oficiais da categoria, com `reference = arquivo.yaml@versao`."""
    out: list[ClaimRule] = []
    for f in rules.prohibited_files(category):
        reference = f"{f.id}.yaml@{f.versao}"
        for r in f.regras:
            out.append(
                ClaimRule(
                    rule_key=r.rule_key,
                    text=r.explicacao,
                    kind=RuleKind.PROIBIDA,
                    source=f.origem,
                    reference=reference,
                    output=r.saida,
                    payload={
                        "tema": r.tema,
                        "termos": list(r.termos),
                        "padroes": list(r.padroes),
                        "junto_de": list(r.junto_de),
                        "sugestao": r.sugestao,
                    },
                )
            )
    for f in rules.files.values():
        if not isinstance(f, In28File) or f.categoria not in (category, "todas"):
            continue
        reference = f"{f.id}.yaml@{f.versao}"
        conditions = {c.nome: c.condicao for c in f.constituintes}
        for claim in f.permitted_claims():
            out.append(
                ClaimRule(
                    rule_key=claim.rule_key,
                    text=claim.texto,
                    kind=RuleKind.PERMITIDA,
                    source=f.origem,
                    reference=reference,
                    output=None,
                    payload={
                        "tema": f"alegação permitida: {claim.constituinte}",
                        "constituinte": claim.constituinte,
                        "condicao": conditions.get(claim.constituinte),
                    },
                )
            )
    return out


def _brand_rules(brand_rules: list) -> list[ClaimRule]:
    out = []
    for i, r in enumerate(brand_rules, start=1):
        terms = [normalize(t).strip() for t in r.termos] or [normalize(r.text).strip()]
        out.append(
            ClaimRule(
                rule_key=r.rule_key or f"MARCA-{i:02d}",
                text=r.text,
                kind=r.kind,
                source=RuleSource.MARCA,
                reference=BRAND_REFERENCE,
                output=(r.output or RuleOutput.BLOQUEAR) if r.kind == RuleKind.PROIBIDA else None,
                payload={"tema": "regra da marca", "termos": terms, "padroes": [], "junto_de": []},
            )
        )
    return out


def name_warnings(
    name: str, category: Category, rules: RuleSet, claim_rules: list[ClaimRule] | None = None
) -> list[NameWarning]:
    """Avisa quando o nome do produto já é alegação (H2, seção 4.7, sinal 3)."""
    candidates = [
        (c.rule_key, c.payload or {}, c.text)
        for c in (claim_rules or [])
        if c.kind == RuleKind.PROIBIDA
    ]
    candidates += [
        (
            r.rule_key,
            {"tema": r.tema, "termos": r.termos, "padroes": r.padroes, "junto_de": r.junto_de},
            r.explicacao,
        )
        for r in rules.h2_patterns.regras
    ]
    if not claim_rules:
        candidates += [
            (
                r.rule_key,
                {"tema": r.tema, "termos": r.termos, "padroes": r.padroes, "junto_de": r.junto_de},
                r.explicacao,
            )
            for r in rules.prohibited_rules(category)
        ]
    warnings: list[NameWarning] = []
    for rule_key, payload, explanation in candidates:
        hits = find_hits(
            name,
            payload.get("termos", ()),
            payload.get("padroes", ()),
            payload.get("junto_de", ()),
        )
        if hits:
            excerpt = name[hits[0].start : hits[0].end]
            warnings.append(
                NameWarning(
                    rule_key=rule_key,
                    excerpt=excerpt,
                    message=(
                        f'O nome do produto contém "{excerpt}" ({payload.get("tema")}). '
                        f"Um nome assim já é uma alegação: {explanation}"
                    ),
                )
            )
    return warnings


# --- Briefing ----------------------------------------------------------------------------


def _money(cents: int) -> str:
    reais = f"{cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {reais.removesuffix(',00')}"


def _conditions(facts: ProductFacts) -> list[str]:
    lines = [f"garantia de {facts.guarantee_days} dias"]
    if facts.access_type == AccessType.VITALICIO:
        lines.append("acesso vitalício")
    elif facts.access_type == AccessType.PRAZO:
        lines.append(f"acesso por {facts.access_months} meses")
    elif facts.access_type == AccessType.ASSINATURA:
        lines.append("acesso enquanto a assinatura estiver ativa")
    billing = {
        Recurrence.UNICA: "pagamento único",
        Recurrence.MENSAL: "assinatura mensal",
        Recurrence.ANUAL: "assinatura anual",
    }[facts.recurrence]
    if facts.auto_renewal:
        billing += " com renovação automática (avise o comprador)"
    lines.append(billing)
    lines.append("bônus: " + ", ".join(facts.bonuses) if facts.bonuses else "sem bônus")
    if facts.extra_costs:
        costs = ", ".join(
            f"{c['descricao']} ({_money(c['valor_mensal_cents'])}/mês)" for c in facts.extra_costs
        )
        lines.append(f"custos extras: {costs}")
    else:
        lines.append("sem custos extras")
    return lines


def build_briefing(
    facts: ProductFacts, product: Product, rules: list[ClaimRule], max_claims: int = 2
) -> str:
    """Texto curto para o creator: condições exatas, pode dizer, não pode dizer, #publi."""
    permitted = [r for r in rules if r.kind == RuleKind.PERMITIDA]
    prohibited = [r for r in rules if r.kind == RuleKind.PROIBIDA]

    can = ["as condições acima, com as mesmas palavras"]
    if permitted:
        shown = [f'"{r.text}"' for r in permitted[:max_claims]]
        rest = len(permitted) - len(shown)
        can.append(
            "; ".join(shown) + (f" (e mais {rest} alegações aprovadas na ficha)" if rest else "")
        )
    temas = list(dict.fromkeys((r.payload or {}).get("tema") or r.text for r in prohibited))
    cannot = ["condição diferente das acima"]
    if temas:
        cannot.append("nada sobre " + ", ".join(temas))
    cannot.append(
        "resultado com número ou prazo, renda com valor, comparação com remédio, urgência falsa"
    )

    lines = [
        f"{product.name}: o que você pode prometer",
        "Condições exatas: " + "; ".join(_conditions(facts)) + ".",
        "Pode dizer: " + "; ".join(can) + ".",
    ]
    if permitted:
        lines.append("As alegações só valem se o produto tiver a dose mínima exigida pela IN 28.")
    lines += [
        "Não pode dizer: " + "; ".join(cannot) + ".",
        "Identifique como publicidade: use #publi.",
    ]
    return "\n".join(lines)


def word_count(text: str) -> int:
    return len(text.split())
