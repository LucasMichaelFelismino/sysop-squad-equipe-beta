"""Consumidor AMQP que entrega os chamados ao Motor de Roteamento."""

from __future__ import annotations

import json
import logging

import pika

from sysop_squad.apresentacao.topologia import (
    EXCHANGE_CHAMADOS,
    FILA_ROTEAMENTO,
    ROTA_ATRIBUIDO,
    ROTA_TRIAGEM_MANUAL,
)
from sysop_squad.dominio.modelo import Chamado
from sysop_squad.dominio.motor import MotorDeRoteamento

log = logging.getLogger(__name__)


class ConsumidorDeChamadosAMQP:
    """Lê a fila de roteamento, roda o motor e publica o resultado.

    - Chamado atribuído        -> chamado.atribuido
    - Chamado sem atribuição    -> chamado.triagem-manual (Driver P2)
    - Mensagem irrecuperável   -> nack sem requeue -> DLQ (ADR 002)
    """

    def __init__(self, canal, motor: MotorDeRoteamento, prefetch: int = 10) -> None:
        self._canal = canal
        self._motor = motor
        self._prefetch = prefetch

    def iniciar(self) -> None:
        self._canal.basic_qos(prefetch_count=self._prefetch)
        self._canal.basic_consume(queue=FILA_ROTEAMENTO, on_message_callback=self.ao_receber)
        self._canal.start_consuming()

    def ao_receber(self, canal, metodo, propriedades, corpo: bytes) -> None:
        try:
            chamado = Chamado.de_dict(json.loads(corpo))
            resultado = self._motor.executar(chamado)
        except Exception:
            log.exception("Mensagem irrecuperável; enviando para a DLQ")
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return

        if resultado.status == "ATRIBUIDO":
            rota = ROTA_ATRIBUIDO
            evento = {
                "chamado_id": chamado.id,
                "consultor_id": resultado.consultor_id,
                "eta_segundos": resultado.eta.total_seconds(),
            }
        else:
            rota = ROTA_TRIAGEM_MANUAL
            evento = {
                "chamado_id": chamado.id,
                "motivo": resultado.motivo,
                "chamado": chamado.para_dict(),
            }

        canal.basic_publish(
            exchange=EXCHANGE_CHAMADOS,
            routing_key=rota,
            body=json.dumps(evento).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                correlation_id=chamado.id,
            ),
        )
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
