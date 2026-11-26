"""Teste de contrato da porta RegistroDeDisponibilidade.

O mesmo conjunto de testes roda contra o dublê em memória e contra o adaptador do Redis,
para o dublê não se comportar diferente do adaptador real (ADR 004).
"""

import threading
import time
from datetime import timedelta

import pytest

from dubles import DisponibilidadeEmMemoria
from sysop_squad.dominio.modelo import Reserva

TTL = timedelta(minutes=5)


@pytest.fixture(params=["memoria", "redis"])
def registro(request):
    if request.param == "memoria":
        return DisponibilidadeEmMemoria()
    fakeredis = pytest.importorskip("fakeredis")
    from sysop_squad.infra.disponibilidade_redis import DisponibilidadeRedisAdapter

    # Um servidor novo por teste, para as reservas de um teste não vazarem para o outro.
    return DisponibilidadeRedisAdapter(fakeredis.FakeRedis(server=fakeredis.FakeServer()))


def test_primeira_reserva_e_aceita(registro):
    assert registro.reservar("c1", "t1", TTL) == Reserva("c1", "t1")


def test_consultor_reservado_recusa_segunda_reserva(registro):
    registro.reservar("c1", "t1", TTL)

    assert registro.reservar("c1", "t2", TTL) is None


def test_consultores_diferentes_sao_independentes(registro):
    registro.reservar("c1", "t1", TTL)

    assert registro.reservar("c2", "t2", TTL) == Reserva("c2", "t2")


def test_liberar_permite_nova_reserva(registro):
    reserva = registro.reservar("c1", "t1", TTL)
    registro.liberar(reserva)

    assert registro.reservar("c1", "t2", TTL) == Reserva("c1", "t2")


def test_liberar_reserva_de_outro_chamado_nao_desfaz_a_atual(registro):
    registro.reservar("c1", "t1", TTL)
    registro.liberar(Reserva("c1", "t-antigo"))

    assert registro.reservar("c1", "t2", TTL) is None


def test_reserva_expira_depois_do_ttl(registro):
    registro.reservar("c1", "t1", timedelta(milliseconds=50))
    time.sleep(0.15)

    assert registro.reservar("c1", "t2", TTL) == Reserva("c1", "t2")


def test_reservas_simultaneas_so_uma_vence(registro):
    """Driver P1: 20 chamados disputando o mesmo consultor ao mesmo tempo."""
    largada = threading.Barrier(20)
    vencedores = []

    def disputar(chamado_id):
        largada.wait()
        if registro.reservar("c1", chamado_id, TTL) is not None:
            vencedores.append(chamado_id)

    threads = [threading.Thread(target=disputar, args=(f"t{i}",)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(vencedores) == 1
