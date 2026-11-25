"""Composition root: o único lugar que conhece as classes concretas e lê configuração.

    python -m sysop_squad.apresentacao.composicao consumidor   # worker AMQP
    python -m sysop_squad.apresentacao.composicao api          # POST /chamados na porta 8000
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from wsgiref.simple_server import make_server

import httpx
import pika
import psycopg
import redis

from sysop_squad.apresentacao.api import RecepcaoDeChamadosAPI
from sysop_squad.apresentacao.consumidor import ConsumidorDeChamadosAMQP
from sysop_squad.apresentacao.servidor_http import criar_aplicacao_wsgi
from sysop_squad.dominio.estrategias import MenorTempoDeDeslocamento
from sysop_squad.dominio.motor import MotorDeRoteamento
from sysop_squad.dominio.portas import ProvedorDeRotas
from sysop_squad.infra.chamados_postgres import ChamadosPostgresAdapter
from sysop_squad.infra.circuit_breaker import CircuitBreakerDeRotas
from sysop_squad.infra.consultores_postgis import ConsultoresPostGISAdapter
from sysop_squad.infra.disponibilidade_redis import DisponibilidadeRedisAdapter
from sysop_squad.infra.mensageria import declarar_topologia
from sysop_squad.infra.rotas_estimadas import RotasEstimadasPorDistancia
from sysop_squad.infra.rotas_maps_http import MapsHTTPAdapter
from sysop_squad.infra.triagem_amqp import TriagemAMQPAdapter

# Abaixo de 2 s, para o fallback do Driver P2 acontecer dentro da meta.
TIMEOUT_MAPAS_SEGUNDOS = 1.5

PADROES = {
    "SYSOP_DATABASE_URL": "postgresql://sysop:sysop@localhost:5432/sysop",
    "SYSOP_REDIS_URL": "redis://localhost:6379/0",
    "SYSOP_AMQP_URL": "amqp://guest:guest@localhost:5672/%2F",
    "SYSOP_MAPAS": "osrm",
    "SYSOP_MAPAS_URL": "https://router.project-osrm.org",
}


class ComposicaoDeDependencias:
    def __init__(self, ambiente: Mapping[str, str] = os.environ) -> None:
        self._ambiente = ambiente

    # Factory Method parametrizado (ADR 007): a escolha da implementação de rotas
    # varia por ambiente e fica concentrada aqui, fora do domínio.
    def criar_provedor_de_rotas(self) -> ProvedorDeRotas:
        modo = self._config("SYSOP_MAPAS")
        if modo == "osrm":
            cliente = httpx.Client(
                base_url=self._config("SYSOP_MAPAS_URL"), timeout=TIMEOUT_MAPAS_SEGUNDOS
            )
            return CircuitBreakerDeRotas(MapsHTTPAdapter(cliente))
        if modo == "local":
            return RotasEstimadasPorDistancia()
        raise ValueError(f"SYSOP_MAPAS deve ser 'osrm' ou 'local', não {modo!r}")

    def motor(self, conexao_bd) -> MotorDeRoteamento:
        return MotorDeRoteamento(
            consultores=ConsultoresPostGISAdapter(conexao_bd),
            disponibilidade=DisponibilidadeRedisAdapter(
                redis.Redis.from_url(self._config("SYSOP_REDIS_URL"))
            ),
            rotas=self.criar_provedor_de_rotas(),
            estrategia=MenorTempoDeDeslocamento(),
        )

    def consumidor(self) -> ConsumidorDeChamadosAMQP:
        canal = self._canal()
        conexao_bd = self._conexao_bd()
        return ConsumidorDeChamadosAMQP(
            canal,
            rotear=self.motor(conexao_bd),
            triagem=TriagemAMQPAdapter(canal),
            chamados=ChamadosPostgresAdapter(conexao_bd),
        )

    def api(self) -> RecepcaoDeChamadosAPI:
        return RecepcaoDeChamadosAPI(self._canal(), ChamadosPostgresAdapter(self._conexao_bd()))

    def _conexao_bd(self):
        return psycopg.connect(self._config("SYSOP_DATABASE_URL"), autocommit=True)

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
    composicao = ComposicaoDeDependencias()
    if sys.argv[1:] == ["api"]:
        make_server("0.0.0.0", 8000, criar_aplicacao_wsgi(composicao.api())).serve_forever()
    else:
        composicao.consumidor().iniciar()
