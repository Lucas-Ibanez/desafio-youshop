"""Erros de domínio com código (CONTEXTO, seção 9)."""

PRODUTO_INEXISTENTE = "PRODUTO_INEXISTENTE"
FICHA_INVALIDA = "FICHA_INVALIDA"
PECA_INEXISTENTE = "PECA_INEXISTENTE"
BLOQUEIO_PENDENTE = "BLOQUEIO_PENDENTE"
FICHA_DESATUALIZADA = "FICHA_DESATUALIZADA"
VENDA_INEXISTENTE = "VENDA_INEXISTENTE"
PAPEL_NAO_AUTORIZADO = "PAPEL_NAO_AUTORIZADO"
PERIODO_INVALIDO = "PERIODO_INVALIDO"


class DomainError(Exception):
    """Erro de negócio. A mensagem é em português e sobe ao usuário como `CODIGO: mensagem`."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
