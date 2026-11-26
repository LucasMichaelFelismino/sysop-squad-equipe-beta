"""POST /chamados segue o Contrato de Dados da Sprint 3 (sprint-3/docs/openapi/chamados.yaml)."""

import copy
from datetime import datetime, timezone

import pytest

pytest.importorskip("pika")

from dubles import CanalFalso, ChamadosEmMemoria  # noqa: E402
from sysop_squad.apresentacao.api import RecepcaoDeChamadosAPI  # noqa: E402

AGORA = datetime(2026, 10, 21, 22, 0, tzinfo=timezone.utc)

# Exemplo do próprio contrato OpenAPI.
EXEMPLO = {
    "idExterno": "LOJA-00821-2026-000145",
    "loja": {"id": "LOJA-00821", "latitude": -25.5352, "longitude": -49.2034},
    "incidente": {"categoria": "PDV", "descricao": "Caixa 02 não inicia após reinicialização"},
    "prioridade": "alta",
    "habilidadesNecessarias": ["suporte_pdv", "hardware"],
    "criadoEm": "2026-10-21T18:40:00-03:00",
}


def _api(canal=None, chamados=None):
    return RecepcaoDeChamadosAPI(
        canal or CanalFalso(),
        chamados or ChamadosEmMemoria(),
        gerar_id=lambda: "CH-1",
        agora=lambda: AGORA,
    )


def _com(**mudancas):
    corpo = copy.deepcopy(EXEMPLO)
    for caminho, valor in mudancas.items():
        alvo, *resto = caminho.split("__")
        if resto:
            corpo[alvo][resto[0]] = valor
        elif valor is None:
            corpo.pop(alvo)
        else:
            corpo[alvo] = valor
    return corpo


def test_exemplo_do_contrato_e_aceito_com_202():
    canal, chamados = CanalFalso(), ChamadosEmMemoria()

    status, corpo = _api(canal, chamados).registrar(EXEMPLO)

    assert status == 202
    assert corpo == {
        "chamadoId": "CH-1",
        "status": "recebido",
        "mensagem": "Chamado recebido para roteamento.",
    }
    assert chamados.obter("CH-1").estado == "REGISTRADO"


def test_content_based_router_manda_prioridade_alta_para_a_fila_prioritaria():
    canal = CanalFalso()

    _api(canal).registrar(EXEMPLO)

    exchange, rota, mensagem, propriedades = canal.publicados[0]
    assert (exchange, rota) == ("chamados", "chamado.registrado.alta")
    assert mensagem["habilidades_exigidas"] == ["hardware", "suporte_pdv"]
    assert mensagem["localizacao"] == [-25.5352, -49.2034]
    assert (propriedades.delivery_mode, propriedades.message_id) == (2, "CH-1")


@pytest.mark.parametrize(
    "corpo",
    [
        _com(idExterno=None),
        _com(loja__latitude=200),
        _com(loja__longitude="-49"),
        _com(incidente__descricao=""),
        _com(prioridade="urgente"),
        _com(habilidadesNecessarias="hardware"),
        _com(habilidadesNecessarias=["pdv", "pdv"]),
        _com(criadoEm="ontem"),
        _com(criadoEm="2026-10-21T18:40:00"),  # sem fuso horário
        "não é objeto",
    ],
)
def test_dados_fora_do_contrato_dao_400_e_nao_publicam(corpo):
    canal = CanalFalso()

    status, _ = _api(canal).registrar(corpo)

    assert status == 400
    assert canal.publicados == []


def test_mesmo_id_externo_da_409():
    chamados = ChamadosEmMemoria()
    _api(chamados=chamados).registrar(EXEMPLO)

    status, _ = _api(chamados=chamados).registrar(EXEMPLO)

    assert status == 409


def test_data_de_criacao_no_futuro_da_422():
    status, _ = _api().registrar(_com(criadoEm="2026-10-23T10:00:00-03:00"))

    assert status == 422


def test_broker_fora_do_ar_da_503_e_libera_o_id_externo_para_reenvio():
    chamados = ChamadosEmMemoria()

    status, _ = _api(CanalFalso(falhar_ao_publicar=True), chamados).registrar(EXEMPLO)
    assert status == 503
    assert chamados.obter("CH-1") is None

    status, _ = _api(CanalFalso(), chamados).registrar(EXEMPLO)
    assert status == 202
