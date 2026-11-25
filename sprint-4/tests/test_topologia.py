"""Topologia do RabbitMQ: Content-Based Router, filas de espera do retry e DLQ (ADR 010)."""

from dubles import CanalFalso
from sysop_squad.infra.mensageria import declarar_topologia


def _topologia():
    canal = CanalFalso()
    declarar_topologia(canal)
    return canal


def test_todas_as_filas_sao_duraveis():
    assert all(fila["duravel"] for fila in _topologia().filas.values())


def test_filas_de_roteamento_mandam_rejeitadas_para_a_dlq():
    canal = _topologia()

    for fila in ("chamados.roteamento", "chamados.roteamento.prioritaria"):
        assert canal.filas[fila]["argumentos"]["x-dead-letter-exchange"] == "chamados.dlx"
    assert ("chamados.dlq", "chamados.dlx", None) in canal.ligacoes


def test_content_based_router_separa_por_prioridade():
    ligacoes = _topologia().ligacoes

    assert ("chamados.roteamento", "chamados", "chamado.registrado.normal") in ligacoes
    assert ("chamados.roteamento", "chamados", "chamado.registrado.baixa") in ligacoes
    assert ("chamados.roteamento.prioritaria", "chamados", "chamado.registrado.alta") in ligacoes
    assert ("chamados.roteamento.prioritaria", "chamados", "chamado.registrado.critica") in ligacoes


def test_filas_de_espera_devolvem_a_mensagem_para_a_exchange_principal():
    canal = _topologia()

    for n in (1, 2):
        assert canal.exchanges[f"chamados.espera.{n}"]["tipo"] == "fanout"
        assert canal.filas[f"chamados.espera.{n}"]["argumentos"] == {
            "x-dead-letter-exchange": "chamados"
        }
        assert (f"chamados.espera.{n}", f"chamados.espera.{n}", None) in canal.ligacoes


def test_declarar_duas_vezes_da_o_mesmo_resultado():
    canal = CanalFalso()
    declarar_topologia(canal)
    primeira = (dict(canal.exchanges), dict(canal.filas), set(canal.ligacoes))
    declarar_topologia(canal)

    assert (canal.exchanges, canal.filas, set(canal.ligacoes)) == primeira
