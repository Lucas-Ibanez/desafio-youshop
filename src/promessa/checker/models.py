"""Tipos do checador: contexto da ficha, achado (formato da seção 9 do CONTEXTO) e resultado."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from promessa.db.enums import AccessType, Category, CheckOutput, CheckSource, Recurrence

Overall = Literal["bloquear", "revisar", "registrar", "limpo"]
SEVERITY = {"bloquear": 3, "revisar": 2, "registrar": 1, "limpo": 0}


class RuleSpec(BaseModel):
    """Uma `claim_rule` da versão da ficha, pronta para casar (vem do `payload`)."""

    rule_key: str
    kind: Literal["permitida", "proibida"]
    text: str
    output: Literal["bloquear", "revisar"] | None = None
    source: str
    tema: str | None = None
    termos: list[str] = Field(default_factory=list)
    padroes: list[str] = Field(default_factory=list)
    junto_de: list[str] = Field(default_factory=list)
    sugestao: str | None = None


class CheckContext(BaseModel):
    """O que a camada 1 precisa da ficha (versão exata), sem acesso ao banco."""

    product_id: str
    category: Category
    facts_id: int
    version: int
    guarantee_days: int
    access_type: AccessType
    access_months: int | None
    recurrence: Recurrence
    auto_renewal: bool
    bonuses: list[str]
    extra_costs: list[dict[str, Any]]
    rules: list[RuleSpec]

    @property
    def prohibited(self) -> list[RuleSpec]:
        return [r for r in self.rules if r.kind == "proibida"]

    @property
    def permitted(self) -> list[RuleSpec]:
        return [r for r in self.rules if r.kind == "permitida"]


class Finding(BaseModel):
    excerpt: str
    span: tuple[int, int]
    output: CheckOutput
    rule_key: str | None
    source: CheckSource = CheckSource.REGRA
    reason_type: str
    explanation: str
    suggestion: str | None = None
    extracted: dict[str, Any] | None = None
    model: str | None = None  # só achados do modelo
    prompt_version: str | None = None


class StoredFinding(Finding):
    """Achado gravado em `check_result` (o `id` é o alvo de uma contestação)."""

    id: int


class Disclosure(BaseModel):
    present: bool
    suggestion: str | None


class Layer1Result(BaseModel):
    findings: list[Finding]
    overall: Overall
    disclosure: Disclosure
    layers_used: list[str] = Field(default_factory=lambda: ["regras"])


class CheckResponse(BaseModel):
    """Resposta de `check_content` (CONTEXTO, seção 9)."""

    piece_id: str
    facts_version: int
    overall: Overall
    findings: list[StoredFinding]
    disclosure: Disclosure
    can_generate_link: bool
    layers_used: list[str]
    notes: list[str] = Field(default_factory=list)


def overall_of(findings: list[Finding]) -> Overall:
    if not findings:
        return "limpo"
    return max((f.output.value for f in findings), key=SEVERITY.__getitem__)  # type: ignore[return-value]
