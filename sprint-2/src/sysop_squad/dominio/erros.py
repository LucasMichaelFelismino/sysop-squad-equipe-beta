"""Erros de domínio.

Os adaptadores traduzem as falhas das bibliotecas (psycopg, redis, httpx) para
estes erros, para que a regra de negócio não precise conhecer nenhuma delas (ADR 004).
"""


class RoteamentoIndisponivelError(Exception):
    """Uma dependência do roteamento não respondeu (banco, cache ou API de Mapas)."""
