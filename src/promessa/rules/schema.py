"""Modelos Pydantic dos YAML de data/rules/ (CONTEXTO, seção 10).

Sintaxe de termo (listas e `junto_de`): texto já normalizado (minúsculas, sem acento), casado
como palavra ou frase inteira; termo terminado em `*` casa como prefixo (`garant*` casa
"garantido" e "garantia").
Padrões (`padroes`, `extratores`) são expressões regulares sobre o texto normalizado.
"""

import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from promessa.db.enums import Category, PromiseAttribute, RuleOutput, RuleSource
from promessa.rules.normalize import normalize

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RuleKey = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]+(-[A-Z0-9]+)*$")]
Status = Literal["pendente_transcricao", "transcrito_a_conferir", "conferido"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_terms(terms: list[str]) -> list[str]:
    for term in terms:
        body = term.removesuffix("*")
        if not body or body != body.strip() or "*" in body:
            raise ValueError(f"termo malformado: {term!r}")
        if normalize(body) != body:
            raise ValueError(f"termo precisa estar normalizado (minúsculas, sem acento): {term!r}")
    return terms


def _check_regexes(patterns: list[str]) -> list[str]:
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"regex inválida {pattern!r}: {e}") from e
    return patterns


class RuleFileHeader(_Strict):
    """Cabeçalho obrigatório de todo arquivo de regras."""

    id: NonEmpty
    versao: NonEmpty
    categoria: Category | Literal["todas"]
    fonte: NonEmpty
    referencia: NonEmpty
    nota: NonEmpty
    origem: RuleSource | None = None  # vira claim_rule.source na materialização (T05)

    def rule_count(self) -> int:
        raise NotImplementedError

    def rule_keys(self) -> list[str]:
        return []


# --- Listas proibidas e padrões da H2 ----------------------------------------------------


class ListRule(_Strict):
    rule_key: RuleKey
    tema: NonEmpty
    saida: RuleOutput
    termos: list[str] = Field(default_factory=list)
    padroes: list[str] = Field(default_factory=list)
    junto_de: list[str] = Field(default_factory=list)  # exige um destes termos no mesmo trecho
    explicacao: NonEmpty
    sugestao: NonEmpty
    # Promessa verificável extraída do trecho (vira registered_promise do tipo resultado, T09)
    extrai: Literal["resultado"] | None = None
    rule_key_vencida: RuleKey | None = None  # só URGENCIA: variante quando a peça é antiga
    explicacao_vencida: str | None = None

    _terms = field_validator("termos", "junto_de")(_check_terms)
    _regex = field_validator("padroes")(_check_regexes)

    @model_validator(mode="after")
    def _has_matcher(self):
        if not self.termos and not self.padroes:
            raise ValueError(f"{self.rule_key}: precisa de `termos` ou `padroes`")
        if (self.rule_key_vencida is None) != (self.explicacao_vencida is None):
            raise ValueError(f"{self.rule_key}: `rule_key_vencida` e `explicacao_vencida` juntos")
        return self


class ListRulesFile(RuleFileHeader):
    """suplemento_proibidas, cosmetico_proibidas e padroes_h2."""

    origem: RuleSource
    regras: list[ListRule] = Field(min_length=1)

    def rule_count(self) -> int:
        return len(self.regras)

    def rule_keys(self) -> list[str]:
        keys = [r.rule_key for r in self.regras]
        keys += [r.rule_key_vencida for r in self.regras if r.rule_key_vencida]
        return keys


# --- Condições da oferta -----------------------------------------------------------------


class Extractor(_Strict):
    """Regex sobre o texto normalizado. Sem `valor` fixo, precisa do grupo `n` (número)."""

    padrao: NonEmpty
    valor: str | None = None

    @model_validator(mode="after")
    def _valid(self):
        _check_regexes([self.padrao])
        compiled = re.compile(self.padrao)
        if self.valor is None and "n" not in compiled.groupindex:
            raise ValueError(f"extrator sem `valor` precisa do grupo (?P<n>...): {self.padrao!r}")
        return self


class OfferConditionRule(_Strict):
    rule_key: RuleKey
    atributo: PromiseAttribute
    extratores: list[Extractor] = Field(min_length=1)
    explicacao: NonEmpty  # quando contradiz a ficha
    sugestao: NonEmpty


class OfferConditionsFile(RuleFileHeader):
    regras: list[OfferConditionRule] = Field(min_length=1)

    def rule_count(self) -> int:
        return len(self.regras)

    def rule_keys(self) -> list[str]:
        return [r.rule_key for r in self.regras]


# --- Normalização ------------------------------------------------------------------------


class NormalizationFile(RuleFileHeader):
    mapa: dict[str, str] = Field(min_length=1)

    @field_validator("mapa")
    @classmethod
    def _one_char(cls, mapa: dict[str, str]) -> dict[str, str]:
        for k, v in mapa.items():
            if len(k) != 1 or len(v) != 1:
                raise ValueError(f"o mapa troca 1 caractere por 1 (posições preservadas): {k}→{v}")
            if not v.isalpha():
                raise ValueError(f"o destino precisa ser letra: {k}→{v}")
        return mapa

    def rule_count(self) -> int:
        return len(self.mapa)


# --- Taxonomia de devolução --------------------------------------------------------------


class Subcause(_Strict):
    subcausa: NonEmpty
    definicao: NonEmpty
    exemplos: list[NonEmpty] = Field(min_length=1)


class Cause(_Strict):
    causa: NonEmpty
    rotulo: NonEmpty
    pesa_no_creator: bool
    nota: NonEmpty
    subcausas: list[Subcause] = Field(min_length=1)


class BoundaryCase(_Strict):
    situacao: NonEmpty
    causa: NonEmpty
    subcausa: NonEmpty
    motivo: NonEmpty


class TaxonomyFile(RuleFileHeader):
    causas: list[Cause] = Field(min_length=1)
    precedencia: list[NonEmpty] = Field(min_length=1)
    casos_de_fronteira: list[BoundaryCase] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self):
        causes = [c.causa for c in self.causas]
        if len(set(causes)) != len(causes):
            raise ValueError("causa repetida")
        subs = [s.subcausa for c in self.causas for s in c.subcausas]
        if len(set(subs)) != len(subs):
            raise ValueError("subcausa repetida (cada subcausa pertence a uma só causa)")
        if sorted(self.precedencia) != sorted(causes):
            raise ValueError("`precedencia` precisa listar cada causa exatamente uma vez")
        by_cause = self.subcauses_by_cause()
        for case in self.casos_de_fronteira:
            if case.subcausa not in by_cause.get(case.causa, ()):
                raise ValueError(
                    f"caso de fronteira com par inválido: {case.causa}/{case.subcausa}"
                )
        return self

    def subcauses_by_cause(self) -> dict[str, list[str]]:
        return {c.causa: [s.subcausa for s in c.subcausas] for c in self.causas}

    def rule_count(self) -> int:
        return sum(len(c.subcausas) for c in self.causas)


# --- IN 28: alegações permitidas ---------------------------------------------------------


class Constituent(_Strict):
    nome: NonEmpty
    codigo: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]+$")]  # IN28-<codigo>-NN
    alegacoes_permitidas: list[NonEmpty] = Field(default_factory=list)
    alegacoes_de_conteudo: list[NonEmpty] = Field(default_factory=list)
    pendente_confirmacao: list[NonEmpty] = Field(default_factory=list)
    condicao: str | None = None


class PermittedClaim(_Strict):
    rule_key: str
    constituinte: str
    texto: str


class In28File(RuleFileHeader):
    origem: RuleSource
    status: Status
    pagina: int | str | None = None
    constituintes: list[Constituent] = Field(min_length=1)

    @model_validator(mode="after")
    def _transcribed(self):
        if self.status != "pendente_transcricao":
            empty = [c.nome for c in self.constituintes if not c.alegacoes_permitidas]
            if empty:
                raise ValueError(f"status {self.status} sem alegações para: {', '.join(empty)}")
        codes = [c.codigo for c in self.constituintes]
        if len(set(codes)) != len(codes):
            raise ValueError("`codigo` de constituinte repetido")
        return self

    def permitted_claims(self) -> list[PermittedClaim]:
        """Uma por alegação permitida, com `rule_key` estável pela ordem no arquivo (D18).

        A ordem não pode mudar: alegação nova entra no fim da lista do constituinte.
        `pendente_confirmacao` não entra.
        """
        if self.status == "pendente_transcricao":
            return []
        return [
            PermittedClaim(rule_key=f"IN28-{c.codigo}-{i:02d}", constituinte=c.nome, texto=text)
            for c in self.constituintes
            for i, text in enumerate(c.alegacoes_permitidas, start=1)
        ]

    def rule_count(self) -> int:
        return len(self.permitted_claims())

    def rule_keys(self) -> list[str]:
        return [p.rule_key for p in self.permitted_claims()]
