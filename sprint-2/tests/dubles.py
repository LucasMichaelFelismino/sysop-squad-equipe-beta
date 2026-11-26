"""Dublês de teste: implementam as portas sem I/O (ADR 004 - testabilidade)."""

from __future__ import annotations

import json
import math
import threading
import time
from datetime import timedelta

from sysop_squad.dominio.erros import RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import ConsultorCandidato, Coordenada, Reserva
from sysop_squad.dominio.portas import (
    ProvedorDeRotas,
    RegistroDeDisponibilidade,
    RepositorioDeConsultores,
)


def distancia_km(a: Coordenada, b: Coordenada) -> float:
    """Distância em linha reta (fórmula de haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


class ConsultoresEmMemoria(RepositorioDeConsultores):
    def __init__(self, consultores: list[ConsultorCandidato]) -> None:
        self._consultores = consultores

    def buscar_candidatos(self, origem, raio_km, habilidades):
        elegiveis = [
            c
            for c in self._consultores
            if habilidades <= c.habilidades and distancia_km(origem, c.posicao) <= raio_km
        ]
        return sorted(elegiveis, key=lambda c: distancia_km(origem, c.posicao))


class DisponibilidadeEmMemoria(RegistroDeDisponibilidade):
    """Mesmo contrato do DisponibilidadeRedisAdapter, sem rede (ver diagrama de classes)."""

    def __init__(self) -> None:
        self._reservas: dict[str, tuple[str, float]] = {}
        self._trava = threading.Lock()

    def reservar(self, consultor_id, chamado_id, ttl):
        with self._trava:
            agora = time.monotonic()
            atual = self._reservas.get(consultor_id)
            if atual is not None and atual[1] > agora:
                return None
            self._reservas[consultor_id] = (str(chamado_id), agora + ttl.total_seconds())
            return Reserva(consultor_id, chamado_id)

    def liberar(self, reserva):
        with self._trava:
            atual = self._reservas.get(reserva.consultor_id)
            if atual is not None and atual[0] == str(reserva.chamado_id):
                del self._reservas[reserva.consultor_id]


class DisponibilidadeForaDoAr(RegistroDeDisponibilidade):
    def reservar(self, consultor_id, chamado_id, ttl):
        raise RoteamentoIndisponivelError("cache fora do ar")

    def liberar(self, reserva):
        raise RoteamentoIndisponivelError("cache fora do ar")


class RotasPorDistancia(ProvedorDeRotas):
    """Tempo = distância em linha reta a uma velocidade média fixa."""

    def __init__(self, velocidade_kmh: float = 40.0) -> None:
        self._velocidade_kmh = velocidade_kmh

    def estimar(self, origem, destino):
        return timedelta(hours=distancia_km(origem, destino) / self._velocidade_kmh)


class RotasFixas(ProvedorDeRotas):
    """Tempo definido pelo teste para cada posição de origem (ex.: trânsito)."""

    def __init__(self, tempos: dict[Coordenada, timedelta]) -> None:
        self._tempos = tempos

    def estimar(self, origem, destino):
        return self._tempos[origem]


class RotasForaDoAr(ProvedorDeRotas):
    def estimar(self, origem, destino):
        raise RoteamentoIndisponivelError("API de Mapas fora do ar")


class CanalFalso:
    """Imita o canal do pika, guardando o que foi publicado, confirmado e rejeitado."""

    def __init__(self) -> None:
        self.publicados: list[tuple[str, str, dict, object]] = []
        self.acks: list[int] = []
        self.nacks: list[tuple[int, bool]] = []

    def basic_publish(self, exchange, routing_key, body, properties=None):
        self.publicados.append((exchange, routing_key, json.loads(body), properties))

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue=True):
        self.nacks.append((delivery_tag, requeue))
