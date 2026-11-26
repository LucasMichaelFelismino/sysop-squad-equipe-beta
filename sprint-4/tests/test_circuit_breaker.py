"""Circuit Breaker na frente da API de Mapas (Política de Retry e Fallback, Sprint 3)."""

from datetime import timedelta

import pytest

from dubles import RotasForaDoAr, RotasPorDistancia
from sysop_squad.dominio.erros import CircuitoAbertoError, RoteamentoIndisponivelError
from sysop_squad.dominio.portas import ProvedorDeRotas
from sysop_squad.infra.circuit_breaker import ABERTO, FECHADO, CircuitBreakerDeRotas

A, B = (-19.92, -43.93), (-19.96, -43.96)


class Relogio:
    def __init__(self) -> None:
        self.agora = 0.0

    def __call__(self) -> float:
        return self.agora


class RotasQueVoltam(ProvedorDeRotas):
    """Falha enquanto `fora_do_ar` for True."""

    def __init__(self) -> None:
        self.fora_do_ar = True
        self.chamadas = 0

    def estimar(self, origem, destino):
        self.chamadas += 1
        if self.fora_do_ar:
            raise RoteamentoIndisponivelError("fora do ar")
        return timedelta(minutes=7)


def _abrir(cb, vezes=3):
    for _ in range(vezes):
        with pytest.raises(RoteamentoIndisponivelError):
            cb.estimar(A, B)


def test_fechado_repassa_a_chamada():
    cb = CircuitBreakerDeRotas(RotasPorDistancia())

    assert cb.estimar(A, B) > timedelta(0)
    assert cb.estado == FECHADO


def test_abre_depois_do_limite_e_para_de_chamar_a_api():
    rotas = RotasForaDoAr()
    cb = CircuitBreakerDeRotas(rotas, limite_de_falhas=3, relogio=Relogio())

    _abrir(cb)
    assert cb.estado == ABERTO

    with pytest.raises(CircuitoAbertoError):
        cb.estimar(A, B)
    assert rotas.chamadas == 3  # a 4ª chamada nem chegou na API


def test_meio_aberto_fecha_se_a_chamada_de_teste_der_certo():
    rotas, relogio = RotasQueVoltam(), Relogio()
    cb = CircuitBreakerDeRotas(rotas, limite_de_falhas=3, tempo_aberto=timedelta(seconds=30), relogio=relogio)
    _abrir(cb)

    relogio.agora = 31.0
    rotas.fora_do_ar = False

    assert cb.estimar(A, B) == timedelta(minutes=7)
    assert cb.estado == FECHADO


def test_meio_aberto_reabre_se_a_chamada_de_teste_falhar():
    rotas, relogio = RotasQueVoltam(), Relogio()
    cb = CircuitBreakerDeRotas(rotas, limite_de_falhas=3, tempo_aberto=timedelta(seconds=30), relogio=relogio)
    _abrir(cb)

    relogio.agora = 31.0
    with pytest.raises(RoteamentoIndisponivelError):
        cb.estimar(A, B)

    assert cb.estado == ABERTO
    with pytest.raises(CircuitoAbertoError):
        cb.estimar(A, B)


def test_sucesso_zera_o_contador_de_falhas():
    rotas = RotasQueVoltam()
    cb = CircuitBreakerDeRotas(rotas, limite_de_falhas=3, relogio=Relogio())
    _abrir(cb, vezes=2)

    rotas.fora_do_ar = False
    cb.estimar(A, B)
    rotas.fora_do_ar = True
    _abrir(cb, vezes=2)

    assert cb.estado == FECHADO
