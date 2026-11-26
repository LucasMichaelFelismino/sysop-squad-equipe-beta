"""O adaptador da API de Mapas traduz falhas HTTP para o erro de domínio (ADR 004)."""

from datetime import timedelta

import pytest

httpx = pytest.importorskip("httpx")

from sysop_squad.dominio.erros import RoteamentoIndisponivelError  # noqa: E402
from sysop_squad.infra.rotas_maps_http import MapsHTTPAdapter  # noqa: E402

ORIGEM = (-19.96, -43.96)
DESTINO = (-19.9245, -43.9352)


def adaptador(responder):
    cliente = httpx.Client(base_url="https://mapas.teste", transport=httpx.MockTransport(responder))
    return MapsHTTPAdapter(cliente)


def test_converte_a_duracao_da_rota_em_timedelta():
    def responder(requisicao):
        assert requisicao.url.path.startswith("/route/v1/driving/")
        return httpx.Response(200, json={"code": "Ok", "routes": [{"duration": 600.0}]})

    assert adaptador(responder).estimar(ORIGEM, DESTINO) == timedelta(minutes=10)


def test_erro_http_vira_erro_de_dominio():
    with pytest.raises(RoteamentoIndisponivelError):
        adaptador(lambda r: httpx.Response(503)).estimar(ORIGEM, DESTINO)


def test_timeout_vira_erro_de_dominio():
    def responder(requisicao):
        raise httpx.ConnectTimeout("demorou demais", request=requisicao)

    with pytest.raises(RoteamentoIndisponivelError):
        adaptador(responder).estimar(ORIGEM, DESTINO)


def test_resposta_sem_rota_vira_erro_de_dominio():
    def responder(requisicao):
        return httpx.Response(200, json={"code": "NoRoute", "routes": []})

    with pytest.raises(RoteamentoIndisponivelError):
        adaptador(responder).estimar(ORIGEM, DESTINO)
