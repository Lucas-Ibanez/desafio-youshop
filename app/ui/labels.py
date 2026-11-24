"""Rótulos da tela (docs/BRAND.md, seção 7.2). O banco e o MCP continuam com os valores originais."""

from __future__ import annotations

DECISION = {
    "bloquear": "Bloqueado",
    "revisar": "Revisar",
    "registrar": "Registrado",
    "limpo": "Sem achados",
}
APPROVAL = {"registrada": "Registrada", "em_revisao": "Em revisão"}
RELATION = {
    "confirma": "Confirma a promessa",
    "contradiz": "Contradiz o registro",
    "sem_relacao": "Sem relação",
    "nao_aplicavel": "Não se aplica",
}
CAUSE = {
    "promessa_explicita": "Promessa do anúncio",
    "promessa_expectativa": "Expectativa",
    "acesso_entrega": "Acesso ou entrega",
    "processo": "Processo",
    "fraude": "Fraude",
    "outros": "Outros",
}
# Visão do creator: "fraude" é do comprador, não dele; mesmo termo da explicação (D39).
CAUSE_FOR_CREATOR = {**CAUSE, "fraude": "Cobrança não reconhecida"}
ROLE = {"marca": "Marca", "creator": "Creator", "operacoes": "Operações"}
REVIEW = {
    "contestado": "Contestado",
    "mantido": "Bloqueio mantido",
    "revertido": "Bloqueio revertido",
}

# Cores fixas das causas nos gráficos (seção 2.4), na ordem da taxonomia.
CAUSE_COLORS = {
    "promessa_explicita": "#4B2FA8",
    "promessa_expectativa": "#9C8AE0",
    "acesso_entrega": "#0E7C7B",
    "processo": "#7D8A9C",
    "fraude": "#8C2F5A",
    "outros": "#B9B4C7",
}

SEVERITY = {"registrar": 1, "revisar": 2, "bloquear": 3}


def label(mapping: dict[str, str], value) -> str:
    raw = getattr(value, "value", value)
    if raw is None:
        return "—"
    return mapping.get(str(raw), str(raw).replace("_", " "))


def origin(rule_key: str | None, facts_version: int | None, prompt_version: str | None) -> str:
    """Origem do achado (seção 7.2): "regra da ficha vN" ou "modelo (prompt X)"."""
    if rule_key:
        return f"regra da ficha v{facts_version}" if facts_version else "regra"
    return f"modelo (prompt {prompt_version})" if prompt_version else "modelo"
