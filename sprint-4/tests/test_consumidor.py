"""Consumidor AMQP: retry exponencial, triagem manual, DLQ e idempotência (ADR 010)."""

import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

pytest.importorskip("pika")

from dubles import CanalFalso, ChamadosEmMemoria, RoteadorFixo, TriagemEmMemoria  # noqa: E402
from sysop_squad.apresentacao.consumidor import ConsumidorDeChamadosAMQP  # noqa: E402
from sysop_squad.chamados.ciclo_de_vida import CicloDeVidaDoChamado  # noqa: E402
from sysop_squad.dominio.erros import (  # noqa: E402
    CircuitoAbertoError,
    RoteamentoIndisponivelError,
)
from sysop_squad.dominio.modelo import Resultado  # noqa: E402

MENSAGEM = {
    "id": "CH-1",
    "loja_id": "LOJA-00821",
    "localizacao": [-25.5352, -49.2034],
    "habilidades_exigidas": ["suporte_pdv"],
    "prioridade": "alta",
}
CORPO = json.dumps(MENSAGEM).encode()
ROTA = "chamado.registrado.alta"


def _cenario(roteador, estado_inicial="REGISTRADO"):
    chamados, triagem, canal = ChamadosEmMemoria(), TriagemEmMemoria(), CanalFalso()
    chamados.registrar("ext-1", CicloDeVidaDoChamado.restaurar("CH-1", estado_inicial), MENSAGEM)
    consumidor = ConsumidorDeChamadosAMQP(
        canal=None,
        rotear=roteador,
        triagem=triagem,
        chamados=chamados,
        sortear_jitter=lambda a, b: 0.1,
    )
    return consumidor, canal, chamados, triagem


def _entregar(consumidor, canal, tentativa=None, corpo=CORPO):
    metodo = SimpleNamespace(delivery_tag=7, routing_key=ROTA)
    propriedades = SimpleNamespace(headers={"x-tentativa": tentativa} if tentativa else None)
    consumidor.ao_receber(canal, metodo, propriedades, corpo)


def test_chamado_atribuido_publica_evento_muda_estado_e_confirma():
    consumidor, canal, chamados, triagem = _cenario(
        RoteadorFixo(Resultado.atribuido("ana", timedelta(minutes=8)))
    )

    _entregar(consumidor, canal)

    _, rota, evento, _ = canal.publicados[0]
    assert (rota, evento["consultor_id"], evento["eta_segundos"]) == ("chamado.atribuido", "ana", 480)
    assert chamados.obter("CH-1").estado == "ATRIBUIDO"
    assert triagem.encaminhados == []
    assert canal.acks == [7]


def test_primeira_falha_transitoria_agenda_retry_de_1_segundo_com_jitter():
    consumidor, canal, chamados, triagem = _cenario(
        RoteadorFixo(erro=RoteamentoIndisponivelError("timeout"))
    )

    _entregar(consumidor, canal)

    exchange, rota, mensagem, propriedades = canal.publicados[0]
    assert (exchange, rota) == ("chamados.espera.1", ROTA)  # volta para a mesma fila
    assert mensagem == MENSAGEM
    assert propriedades.expiration == "1100"  # 1 s + 0,1 s de jitter
    assert propriedades.headers == {"x-tentativa": 2}
    assert chamados.obter("CH-1").estado == "EM_ROTEAMENTO"
    assert triagem.encaminhados == []
    assert canal.acks == [7]


def test_segunda_falha_espera_2_segundos():
    consumidor, canal, _, _ = _cenario(RoteadorFixo(erro=RoteamentoIndisponivelError("timeout")))

    _entregar(consumidor, canal, tentativa=2)

    exchange, _, _, propriedades = canal.publicados[0]
    assert (exchange, propriedades.expiration) == ("chamados.espera.2", "2100")
    assert propriedades.headers == {"x-tentativa": 3}


def test_terceira_falha_vai_para_triagem_manual():
    consumidor, canal, chamados, triagem = _cenario(
        RoteadorFixo(erro=RoteamentoIndisponivelError("timeout"))
    )

    _entregar(consumidor, canal, tentativa=3)

    assert canal.publicados == []
    assert triagem.encaminhados[0][0] == "CH-1"
    assert "após 3 tentativas" in triagem.encaminhados[0][1]
    assert chamados.obter("CH-1").estado == "EM_TRIAGEM_MANUAL"
    assert canal.acks == [7]


def test_circuito_aberto_vai_direto_para_triagem_sem_retry():
    consumidor, canal, chamados, triagem = _cenario(
        RoteadorFixo(erro=CircuitoAbertoError("aberto"))
    )

    _entregar(consumidor, canal)

    assert canal.publicados == []
    assert len(triagem.encaminhados) == 1
    assert chamados.obter("CH-1").estado == "EM_TRIAGEM_MANUAL"


def test_sem_consultor_disponivel_vai_para_triagem():
    consumidor, canal, chamados, triagem = _cenario(
        RoteadorFixo(Resultado.triagem_manual("todos os candidatos estão ocupados"))
    )

    _entregar(consumidor, canal)

    assert triagem.encaminhados == [("CH-1", "todos os candidatos estão ocupados")]


@pytest.mark.parametrize("estado", ["ATRIBUIDO", "EM_TRIAGEM_MANUAL", "CANCELADO"])
def test_reentrega_de_chamado_ja_resolvido_so_confirma(estado):
    """Idempotência: a mesma mensagem não gera dois roteamentos nem duas triagens."""
    consumidor, canal, chamados, triagem = _cenario(
        RoteadorFixo(Resultado.atribuido("bruno", timedelta(minutes=3))), estado_inicial=estado
    )

    _entregar(consumidor, canal)

    assert canal.publicados == []
    assert triagem.encaminhados == []
    assert chamados.obter("CH-1").estado == estado
    assert canal.acks == [7]


@pytest.mark.parametrize("corpo", [b"isto nao e json", json.dumps({"id": "CH-1"}).encode()])
def test_mensagem_irrecuperavel_vai_para_a_dlq(corpo):
    consumidor, canal, _, _ = _cenario(RoteadorFixo(Resultado.atribuido("ana", timedelta(1))))

    _entregar(consumidor, canal, corpo=corpo)

    assert canal.publicados == []
    assert canal.nacks == [(7, False)]


def test_chamado_desconhecido_vai_para_a_dlq():
    consumidor, canal, chamados, _ = _cenario(RoteadorFixo(Resultado.atribuido("ana", timedelta(1))))
    chamados.descartar("CH-1")

    _entregar(consumidor, canal)

    assert canal.nacks == [(7, False)]


def test_erro_inesperado_vai_para_a_dlq_em_vez_de_repetir_para_sempre():
    consumidor, canal, _, triagem = _cenario(RoteadorFixo(erro=ZeroDivisionError("bug")))

    _entregar(consumidor, canal)

    assert canal.nacks == [(7, False)]
    assert triagem.encaminhados == []
