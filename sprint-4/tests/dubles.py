"""Dublês de teste: implementam as portas sem I/O (ADR 004 da Sprint 2 - testabilidade)."""

from __future__ import annotations

import json
import math
import threading
import time
from datetime import timedelta

from sysop_squad.chamados.ciclo_de_vida import CicloDeVidaDoChamado
from sysop_squad.chamados.portas import RepositorioDeChamados
from sysop_squad.dominio.erros import CircuitoAbertoError, RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import ConsultorCandidato, Coordenada, Reserva
from sysop_squad.dominio.portas import (
    FilaDeTriagemManual,
    ProvedorDeRotas,
    RegistroDeDisponibilidade,
    RepositorioDeConsultores,
    RotearChamado,
)


def distancia_km(a: Coordenada, b: Coordenada) -> float:
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
    """Mesmo contrato do DisponibilidadeRedisAdapter, sem rede."""

    def __init__(self) -> None:
        self._reservas: dict[str, tuple[str, float]] = {}
        self._trava = threading.Lock()

    def reservar(self, consultor_id, chamado_id, ttl):
        with self._trava:
            agora = time.monotonic()
            atual = self._reservas.get(consultor_id)
            if atual is not None and atual[1] > agora and atual[0] != str(chamado_id):
                return None
            if atual is None or atual[1] <= agora:
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
    def __init__(self) -> None:
        self.chamadas = 0

    def estimar(self, origem, destino):
        self.chamadas += 1
        raise RoteamentoIndisponivelError("API de Mapas fora do ar")


class RoteadorFixo(RotearChamado):
    """Devolve um resultado pronto ou levanta um erro, para testar o consumidor."""

    def __init__(self, resultado=None, erro: Exception | None = None) -> None:
        self._resultado = resultado
        self._erro = erro

    def executar(self, chamado):
        if self._erro is not None:
            raise self._erro
        return self._resultado


class TriagemEmMemoria(FilaDeTriagemManual):
    def __init__(self) -> None:
        self.encaminhados: list[tuple[str, str]] = []

    def encaminhar(self, chamado, motivo):
        self.encaminhados.append((chamado.id, motivo))


class ChamadosEmMemoria(RepositorioDeChamados):
    def __init__(self) -> None:
        self.por_id: dict[str, CicloDeVidaDoChamado] = {}
        self.dados: dict[str, dict] = {}
        self._ids_externos: dict[str, str] = {}

    def registrar(self, id_externo, ciclo, dados):
        if id_externo in self._ids_externos:
            return False
        self._ids_externos[id_externo] = ciclo.chamado_id
        self.por_id[ciclo.chamado_id] = ciclo
        self.dados[ciclo.chamado_id] = dados
        return True

    def descartar(self, chamado_id):
        self.por_id.pop(chamado_id, None)
        self.dados.pop(chamado_id, None)
        self._ids_externos = {k: v for k, v in self._ids_externos.items() if v != chamado_id}

    def obter(self, chamado_id):
        return self.por_id.get(chamado_id)

    def salvar(self, ciclo):
        self.por_id[ciclo.chamado_id] = ciclo


class CanalFalso:
    """Imita o canal do pika: guarda publicações, acks, nacks e declarações."""

    def __init__(self, falhar_ao_publicar: bool = False) -> None:
        self.publicados: list[tuple[str, str, dict, object]] = []
        self.acks: list[int] = []
        self.nacks: list[tuple[int, bool]] = []
        self.exchanges: dict[str, dict] = {}
        self.filas: dict[str, dict] = {}
        self.ligacoes: list[tuple[str, str, str | None]] = []
        self._falhar_ao_publicar = falhar_ao_publicar

    def basic_publish(self, exchange, routing_key, body, properties=None):
        if self._falhar_ao_publicar:
            raise ConnectionError("broker fora do ar")
        self.publicados.append((exchange, routing_key, json.loads(body), properties))

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue=True):
        self.nacks.append((delivery_tag, requeue))

    def exchange_declare(self, exchange, exchange_type="direct", durable=False):
        self.exchanges[exchange] = {"tipo": exchange_type, "duravel": durable}

    def queue_declare(self, queue, durable=False, arguments=None):
        self.filas[queue] = {"duravel": durable, "argumentos": arguments or {}}

    def queue_bind(self, queue, exchange, routing_key=None):
        self.ligacoes.append((queue, exchange, routing_key))


__all__ = [
    "CanalFalso",
    "ChamadosEmMemoria",
    "CircuitoAbertoError",
    "ConsultoresEmMemoria",
    "DisponibilidadeEmMemoria",
    "DisponibilidadeForaDoAr",
    "RoteadorFixo",
    "RotasFixas",
    "RotasForaDoAr",
    "RotasPorDistancia",
    "TriagemEmMemoria",
    "distancia_km",
]
