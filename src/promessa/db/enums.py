"""Enums de domínio (CONTEXTO, seção 8.1).

Valores em português sem acento, porque aparecem para o usuário. `cause` e `subcause` da
devolução não estão aqui: a taxonomia é dado (data/rules/taxonomia_devolucao.yaml, T03).
"""

from enum import StrEnum


class Category(StrEnum):
    SUPLEMENTO = "suplemento"
    COSMETICO = "cosmetico"
    INFOPRODUTO_RENDA = "infoproduto_renda"
    INFOPRODUTO_OUTRO = "infoproduto_outro"


class AccessType(StrEnum):
    VITALICIO = "vitalicio"
    PRAZO = "prazo"
    ASSINATURA = "assinatura"
    NAO_APLICA = "nao_aplica"


class Recurrence(StrEnum):
    UNICA = "unica"
    MENSAL = "mensal"
    ANUAL = "anual"


class RuleKind(StrEnum):
    PERMITIDA = "permitida"
    PROIBIDA = "proibida"


class RuleSource(StrEnum):
    IN28 = "IN28"
    ANVISA = "ANVISA"
    RDC752 = "RDC752"
    CONAR = "CONAR"
    CDC = "CDC"
    MARCA = "MARCA"


class RuleOutput(StrEnum):
    """Saída de uma regra proibida."""

    BLOQUEAR = "bloquear"
    REVISAR = "revisar"


class Channel(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    WHATSAPP = "whatsapp"
    OUTRO = "outro"


class SubmittedBy(StrEnum):
    CREATOR = "creator"
    MARCA = "marca"


class CheckOutput(StrEnum):
    """Saída de um trecho checado. `limpo` só existe no `overall` da peça, não por trecho."""

    BLOQUEAR = "bloquear"
    REVISAR = "revisar"
    REGISTRAR = "registrar"


class CheckSource(StrEnum):
    REGRA = "regra"
    MODELO = "modelo"


class ReviewStatus(StrEnum):
    NAO_APLICAVEL = "nao_aplicavel"
    CONTESTADO = "contestado"
    MANTIDO = "mantido"
    REVERTIDO = "revertido"


class PromiseType(StrEnum):
    CONDICAO_OFERTA = "condicao_oferta"
    RESULTADO = "resultado"
    ALEGACAO = "alegacao"


class PromiseAttribute(StrEnum):
    GARANTIA = "garantia"
    ACESSO = "acesso"
    RECORRENCIA = "recorrencia"
    BONUS = "bonus"
    CUSTO = "custo"
    RESULTADO = "resultado"
    OUTRO = "outro"


class Approval(StrEnum):
    REGISTRADA = "registrada"
    EM_REVISAO = "em_revisao"


class ActorType(StrEnum):
    HUMANO = "humano"
    AGENTE = "agente"


class RefundType(StrEnum):
    REEMBOLSO = "reembolso"
    CHARGEBACK = "chargeback"
    TICKET = "ticket"


class Relation(StrEnum):
    CONFIRMA = "confirma"
    CONTRADIZ = "contradiz"
    SEM_RELACAO = "sem_relacao"
    NAO_APLICAVEL = "nao_aplicavel"


class ReviewAction(StrEnum):
    CONTESTAR = "contestar"
    MANTER = "manter"
    REVERTER = "reverter"
    APROVAR = "aprovar"
    RECLASSIFICAR = "reclassificar"


class Role(StrEnum):
    """Papel de quem age (CONTEXTO, seção 4). É parâmetro, não login."""

    MARCA = "marca"
    CREATOR = "creator"
    OPERACOES = "operacoes"
    SISTEMA = "sistema"
