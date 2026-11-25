"""API de Recepção e consumidor AMQP, com um canal falso no lugar do RabbitMQ."""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("pika")

from dubles import (  # noqa: E402
    CanalFalso,
    ConsultoresEmMemoria,
    DisponibilidadeEmMemoria,
    RotasForaDoAr,
    RotasPorDistancia,
)
from sysop_squad.apresentacao.api import RecepcaoDeChamadosAPI  # noqa: E402
from sysop_squad.apresentacao.consumidor import ConsumidorDeChamadosAMQP  # noqa: E402
from sysop_squad.dominio.modelo import ConsultorCandidato  # noqa: E402
from sysop_squad.dominio.motor import MotorDeRoteamento  # noqa: E402

LOJA = [-19.9245, -43.9352]
ANA = ConsultorCandidato("ana", (-19.93, -43.94), frozenset({"pdv"}))
CORPO_VALIDO = {"loja_id": "loja-42", "localizacao": LOJA, "habilidades_exigidas": ["pdv"]}


def test_api_publica_o_chamado_e_responde_202():
    canal = CanalFalso()
    api = RecepcaoDeChamadosAPI(canal, gerar_id=lambda: "t-1")

    status, corpo = api.abrir(CORPO_VALIDO)

    assert (status, corpo) == (202, {"id": "t-1", "status": "ACEITO"})
    exchange, rota, mensagem, propriedades = canal.publicados[0]
    assert (exchange, rota) == ("chamados", "chamado.aberto")
    assert mensagem["habilidades_exigidas"] == ["pdv"]
    assert propriedades.delivery_mode == 2
    assert propriedades.message_id == "t-1"


@pytest.mark.parametrize(
    "corpo",
    [
        {"loja_id": "loja-42"},  # sem localização
        {**CORPO_VALIDO, "localizacao": [200, 0]},  # fora do intervalo
        {**CORPO_VALIDO, "habilidades_exigidas": "pdv"},  # texto em vez de lista
    ],
)
def test_api_recusa_chamado_invalido_sem_publicar(corpo):
    canal = CanalFalso()

    status, _ = RecepcaoDeChamadosAPI(canal).abrir(corpo)

    assert status == 400
    assert canal.publicados == []


def _mensagem(corpo: dict) -> bytes:
    return json.dumps({"id": "t-1", **corpo}).encode()


def _consumidor(rotas):
    motor = MotorDeRoteamento(ConsultoresEmMemoria([ANA]), DisponibilidadeEmMemoria(), rotas)
    return ConsumidorDeChamadosAMQP(canal=None, motor=motor)


def test_consumidor_publica_chamado_atribuido_e_confirma():
    canal = CanalFalso()

    _consumidor(RotasPorDistancia()).ao_receber(
        canal, SimpleNamespace(delivery_tag=7), None, _mensagem(CORPO_VALIDO)
    )

    _, rota, evento, _ = canal.publicados[0]
    assert rota == "chamado.atribuido"
    assert evento["consultor_id"] == "ana"
    assert canal.acks == [7]


def test_consumidor_manda_para_triagem_manual_quando_o_roteamento_falha():
    canal = CanalFalso()

    _consumidor(RotasForaDoAr()).ao_receber(
        canal, SimpleNamespace(delivery_tag=8), None, _mensagem(CORPO_VALIDO)
    )

    _, rota, evento, _ = canal.publicados[0]
    assert rota == "chamado.triagem-manual"
    assert evento["chamado"]["loja_id"] == "loja-42"
    assert canal.acks == [8]


def test_consumidor_rejeita_mensagem_irrecuperavel_para_a_dlq():
    canal = CanalFalso()

    _consumidor(RotasPorDistancia()).ao_receber(
        canal, SimpleNamespace(delivery_tag=9), None, b"isto nao e json"
    )

    assert canal.publicados == []
    assert canal.nacks == [(9, False)]
