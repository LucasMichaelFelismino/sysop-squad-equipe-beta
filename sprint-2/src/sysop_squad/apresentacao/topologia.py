"""Filas e exchanges do RabbitMQ usados pela borda (ADR 000 e ADR 002).

    chamado.aberto ──► [chamados] ──► chamados.roteamento ──► Motor de Roteamento
                           │
                           ├── chamado.atribuido ──────► chamados.atribuidos (notificação ao consultor)
                           └── chamado.triagem-manual ─► chamados.triagem-manual (Painel Operacional)

    Mensagem rejeitada sem requeue em chamados.roteamento ──► [chamados.dlx] ──► chamados.dlq
"""

from __future__ import annotations

EXCHANGE_CHAMADOS = "chamados"
EXCHANGE_DLX = "chamados.dlx"

ROTA_ABERTO = "chamado.aberto"
ROTA_ATRIBUIDO = "chamado.atribuido"
ROTA_TRIAGEM_MANUAL = "chamado.triagem-manual"

FILA_ROTEAMENTO = "chamados.roteamento"
FILA_ATRIBUIDOS = "chamados.atribuidos"
FILA_TRIAGEM_MANUAL = "chamados.triagem-manual"
FILA_DLQ = "chamados.dlq"


def declarar_topologia(canal) -> None:
    """Declara exchanges e filas duráveis. É idempotente: pode rodar a cada inicialização."""
    canal.exchange_declare(EXCHANGE_CHAMADOS, exchange_type="topic", durable=True)
    canal.exchange_declare(EXCHANGE_DLX, exchange_type="fanout", durable=True)

    canal.queue_declare(
        FILA_ROTEAMENTO, durable=True, arguments={"x-dead-letter-exchange": EXCHANGE_DLX}
    )
    canal.queue_bind(FILA_ROTEAMENTO, EXCHANGE_CHAMADOS, routing_key=ROTA_ABERTO)

    canal.queue_declare(FILA_ATRIBUIDOS, durable=True)
    canal.queue_bind(FILA_ATRIBUIDOS, EXCHANGE_CHAMADOS, routing_key=ROTA_ATRIBUIDO)

    canal.queue_declare(FILA_TRIAGEM_MANUAL, durable=True)
    canal.queue_bind(FILA_TRIAGEM_MANUAL, EXCHANGE_CHAMADOS, routing_key=ROTA_TRIAGEM_MANUAL)

    canal.queue_declare(FILA_DLQ, durable=True)
    canal.queue_bind(FILA_DLQ, EXCHANGE_DLX)
