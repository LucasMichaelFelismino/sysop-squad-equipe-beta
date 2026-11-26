"""Factory Method parametrizado da composição (ADR 007)."""

import pytest

pytest.importorskip("psycopg")
pytest.importorskip("pika")

from sysop_squad.apresentacao.composicao import ComposicaoDeDependencias  # noqa: E402
from sysop_squad.dominio.portas import ProvedorDeRotas  # noqa: E402
from sysop_squad.infra.circuit_breaker import CircuitBreakerDeRotas  # noqa: E402
from sysop_squad.infra.rotas_estimadas import RotasEstimadasPorDistancia  # noqa: E402


def test_producao_usa_a_api_de_mapas_atras_do_circuit_breaker():
    provedor = ComposicaoDeDependencias({"SYSOP_MAPAS": "osrm"}).criar_provedor_de_rotas()

    assert isinstance(provedor, CircuitBreakerDeRotas)


def test_ambiente_local_usa_estimativa_sem_rede():
    provedor = ComposicaoDeDependencias({"SYSOP_MAPAS": "local"}).criar_provedor_de_rotas()

    assert isinstance(provedor, RotasEstimadasPorDistancia)


def test_toda_opcao_devolve_algo_que_cumpre_o_contrato_do_dominio():
    for modo in ("osrm", "local"):
        provedor = ComposicaoDeDependencias({"SYSOP_MAPAS": modo}).criar_provedor_de_rotas()
        assert isinstance(provedor, ProvedorDeRotas)


def test_opcao_desconhecida_falha_na_inicializacao():
    with pytest.raises(ValueError):
        ComposicaoDeDependencias({"SYSOP_MAPAS": "google"}).criar_provedor_de_rotas()
