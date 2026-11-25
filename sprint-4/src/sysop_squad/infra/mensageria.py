"""Topologia do RabbitMQ: Content-Based Router, retry exponencial e DLQ (ADR 010).

                                   ┌─ chamado.registrado.baixa|normal ─► chamados.roteamento ─────────────┐
    API ── chamado.registrado.* ─► [chamados] (topic)                                                         ├─► consumidor
                                   └─ chamado.registrado.alta|critica ─► chamados.roteamento.prioritaria ─┘
                                                                                                        │
         falha transitória (tentativa 1) ─► [chamados.espera.1] ─► chamados.espera.1 (expira em ~1 s) ──┤
         falha transitória (tentativa 2) ─► [chamados.espera.2] ─► chamados.espera.2 (expira em ~2 s) ──┤ volta para [chamados]
                                                                                                        │ com a rota original
         3ª falha ou circuito aberto ─────► chamado.triagem-manual ─► chamados.triagem-manual (Painel)
         atribuído ───────────────────────► chamado.atribuido ─────► chamados.atribuidos (notificação)
         mensagem irrecuperável (nack) ───► [chamados.dlx] ─────────► chamados.dlq (alerta operacional)

As filas de espera não têm consumidor: a mensagem fica lá até a expiração e o RabbitMQ a
devolve (dead-letter) para a exchange principal, com a mesma chave de roteamento.
"""

from __future__ import annotations

from datetime import timedelta

EXCHANGE_CHAMADOS = "chamados"
EXCHANGE_DLX = "chamados.dlx"

ROTA_ATRIBUIDO = "chamado.atribuido"
ROTA_TRIAGEM_MANUAL = "chamado.triagem-manual"

FILA_ROTEAMENTO = "chamados.roteamento"
FILA_ROTEAMENTO_PRIORITARIA = "chamados.roteamento.prioritaria"
FILA_ATRIBUIDOS = "chamados.atribuidos"
FILA_TRIAGEM_MANUAL = "chamados.triagem-manual"
FILA_DLQ = "chamados.dlq"

PRIORIDADES_NORMAIS = ("baixa", "normal")
PRIORIDADES_URGENTES = ("alta", "critica")

# Backoff exponencial da Política de Retry (Sprint 3): 3 tentativas no total,
# esperando ~1 s antes da 2ª e ~2 s antes da 3ª, mais um jitter aleatório.
ESPERAS = (timedelta(seconds=1), timedelta(seconds=2))
JITTER_MAXIMO = timedelta(milliseconds=250)
TENTATIVAS_MAXIMAS = len(ESPERAS) + 1

CABECALHO_TENTATIVA = "x-tentativa"


def rota_de_entrada(prioridade: str) -> str:
    """Chave de roteamento do Content-Based Router (ADR 005 da Sprint 3)."""
    return f"chamado.registrado.{prioridade}"


def exchange_de_espera(tentativa: int) -> str:
    return f"chamados.espera.{tentativa}"


def fila_de_espera(tentativa: int) -> str:
    return f"chamados.espera.{tentativa}"


def declarar_topologia(canal) -> None:
    """Declara exchanges e filas duráveis. É idempotente: pode rodar a cada inicialização."""
    canal.exchange_declare(EXCHANGE_CHAMADOS, exchange_type="topic", durable=True)
    canal.exchange_declare(EXCHANGE_DLX, exchange_type="fanout", durable=True)

    # Content-Based Router: a prioridade decide a fila de roteamento.
    for fila, prioridades in (
        (FILA_ROTEAMENTO, PRIORIDADES_NORMAIS),
        (FILA_ROTEAMENTO_PRIORITARIA, PRIORIDADES_URGENTES),
    ):
        canal.queue_declare(fila, durable=True, arguments={"x-dead-letter-exchange": EXCHANGE_DLX})
        for prioridade in prioridades:
            canal.queue_bind(fila, EXCHANGE_CHAMADOS, routing_key=rota_de_entrada(prioridade))

    # Filas de espera do retry: expiram e devolvem a mensagem para a exchange principal.
    for tentativa in range(1, len(ESPERAS) + 1):
        canal.exchange_declare(exchange_de_espera(tentativa), exchange_type="fanout", durable=True)
        canal.queue_declare(
            fila_de_espera(tentativa),
            durable=True,
            arguments={"x-dead-letter-exchange": EXCHANGE_CHAMADOS},
        )
        canal.queue_bind(fila_de_espera(tentativa), exchange_de_espera(tentativa))

    canal.queue_declare(FILA_ATRIBUIDOS, durable=True)
    canal.queue_bind(FILA_ATRIBUIDOS, EXCHANGE_CHAMADOS, routing_key=ROTA_ATRIBUIDO)

    canal.queue_declare(FILA_TRIAGEM_MANUAL, durable=True)
    canal.queue_bind(FILA_TRIAGEM_MANUAL, EXCHANGE_CHAMADOS, routing_key=ROTA_TRIAGEM_MANUAL)

    canal.queue_declare(FILA_DLQ, durable=True)
    canal.queue_bind(FILA_DLQ, EXCHANGE_DLX)
