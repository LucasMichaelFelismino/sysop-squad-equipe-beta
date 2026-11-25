"""Composition root: o único lugar que conhece as classes concretas e lê configuração (ADR 004).

Para rodar o consumidor:  python -m sysop_squad.apresentacao.composicao
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

import httpx
import pika
import psycopg
import redis

from sysop_squad.apresentacao.api import RecepcaoDeChamadosAPI
from sysop_squad.apresentacao.consumidor import ConsumidorDeChamadosAMQP
from sysop_squad.apresentacao.topologia import declarar_topologia
from sysop_squad.dominio.motor import MotorDeRoteamento
from sysop_squad.infra.consultores_postgis import ConsultoresPostGISAdapter
from sysop_squad.infra.disponibilidade_redis import DisponibilidadeRedisAdapter
from sysop_squad.infra.rotas_maps_http import MapsHTTPAdapter

# Abaixo de 2 s, para o fallback do Driver P2 acontecer dentro da meta.
TIMEOUT_MAPAS_SEGUNDOS = 1.5

PADROES = {
    "SYSOP_DATABASE_URL": "postgresql://localhost:5432/sysop",
    "SYSOP_REDIS_URL": "redis://localhost:6379/0",
    "SYSOP_MAPAS_URL": "https://router.project-osrm.org",
    "SYSOP_AMQP_URL": "amqp://guest:guest@localhost:5672/%2F",
}


class ComposicaoDeDependencias:
    def __init__(self, ambiente: Mapping[str, str] = os.environ) -> None:
        self._ambiente = ambiente

    def motor(self) -> MotorDeRoteamento:
        return MotorDeRoteamento(
            consultores=ConsultoresPostGISAdapter(
                psycopg.connect(self._config("SYSOP_DATABASE_URL"), autocommit=True)
            ),
            disponibilidade=DisponibilidadeRedisAdapter(
                redis.Redis.from_url(self._config("SYSOP_REDIS_URL"))
            ),
            rotas=MapsHTTPAdapter(
                httpx.Client(
                    base_url=self._config("SYSOP_MAPAS_URL"), timeout=TIMEOUT_MAPAS_SEGUNDOS
                )
            ),
        )

    def consumidor(self) -> ConsumidorDeChamadosAMQP:
        return ConsumidorDeChamadosAMQP(self._canal(), self.motor())

    def api(self) -> RecepcaoDeChamadosAPI:
        return RecepcaoDeChamadosAPI(self._canal())

    def _canal(self):
        conexao = pika.BlockingConnection(pika.URLParameters(self._config("SYSOP_AMQP_URL")))
        canal = conexao.channel()
        canal.confirm_delivery()  # o 202 só sai depois que o broker confirma (Driver P1)
        declarar_topologia(canal)
        return canal

    def _config(self, chave: str) -> str:
        return self._ambiente.get(chave, PADROES[chave])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ComposicaoDeDependencias().consumidor().iniciar()
