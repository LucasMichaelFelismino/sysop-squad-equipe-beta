"""Adaptador da fila de triagem manual no RabbitMQ (Driver P2)."""

from __future__ import annotations

import json

import pika

from sysop_squad.dominio.modelo import Chamado
from sysop_squad.dominio.portas import FilaDeTriagemManual
from sysop_squad.infra.mensageria import EXCHANGE_CHAMADOS, ROTA_TRIAGEM_MANUAL


class TriagemAMQPAdapter(FilaDeTriagemManual):
    def __init__(self, canal) -> None:
        self._canal = canal

    def encaminhar(self, chamado: Chamado, motivo: str) -> None:
        evento = {"chamado_id": chamado.id, "motivo": motivo, "chamado": chamado.para_dict()}
        self._canal.basic_publish(
            exchange=EXCHANGE_CHAMADOS,
            routing_key=ROTA_TRIAGEM_MANUAL,
            body=json.dumps(evento, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=f"triagem-{chamado.id}",  # o Painel descarta duplicatas por este id
                correlation_id=chamado.id,
            ),
        )
