"""Erros de domínio do roteamento.

Os adaptadores traduzem as falhas das bibliotecas (psycopg, redis, httpx) para estes
erros, para que a regra de negócio não precise conhecer nenhuma delas (ADR 004 da Sprint 2).
"""


class RoteamentoIndisponivelError(Exception):
    """Falha transitória: uma dependência do roteamento não respondeu (banco, cache ou mapas).

    Quem chama o motor decide entre tentar de novo e mandar para a triagem (ADR 010).
    """


class CircuitoAbertoError(RoteamentoIndisponivelError):
    """O Circuit Breaker está aberto: não adianta tentar de novo agora.

    A Política de Retry da Sprint 3 manda o chamado direto para a triagem manual.
    """
