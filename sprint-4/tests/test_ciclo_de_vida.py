"""Padrão State no ciclo de vida do chamado (ADR 012)."""

import pytest

from sysop_squad.chamados.ciclo_de_vida import CicloDeVidaDoChamado, TransicaoInvalidaError


def test_chamado_novo_comeca_registrado_e_aceita_roteamento():
    ciclo = CicloDeVidaDoChamado("t1")

    assert ciclo.estado == "REGISTRADO"
    assert ciclo.aceita_roteamento


def test_caminho_feliz_ate_fechar():
    ciclo = CicloDeVidaDoChamado("t1")

    ciclo.iniciar_roteamento()
    ciclo.atribuir("ana")
    ciclo.iniciar_atendimento()
    ciclo.resolver()
    ciclo.fechar()

    assert ciclo.estado == "FECHADO"
    assert ciclo.final
    assert ciclo.consultor_id == "ana"
    assert [estado for estado, _ in ciclo.historico] == [
        "REGISTRADO",
        "EM_ROTEAMENTO",
        "ATRIBUIDO",
        "EM_ATENDIMENTO",
        "RESOLVIDO",
        "FECHADO",
    ]


def test_falha_no_roteamento_leva_para_triagem_e_o_operador_atribui():
    ciclo = CicloDeVidaDoChamado("t1")
    ciclo.iniciar_roteamento()

    ciclo.encaminhar_para_triagem("API de Mapas indisponível")
    assert ciclo.estado == "EM_TRIAGEM_MANUAL"
    assert not ciclo.aceita_roteamento
    assert ciclo.historico[-1] == ("EM_TRIAGEM_MANUAL", "API de Mapas indisponível")

    ciclo.atribuir("bruno")
    assert (ciclo.estado, ciclo.consultor_id) == ("ATRIBUIDO", "bruno")


def test_nova_tentativa_de_roteamento_continua_no_mesmo_estado():
    ciclo = CicloDeVidaDoChamado("t1")
    ciclo.iniciar_roteamento()
    ciclo.iniciar_roteamento()  # mensagem voltou da fila de espera

    assert ciclo.estado == "EM_ROTEAMENTO"


def test_consultor_que_nao_pode_atender_devolve_para_triagem():
    ciclo = CicloDeVidaDoChamado("t1")
    ciclo.iniciar_roteamento()
    ciclo.atribuir("ana")

    ciclo.encaminhar_para_triagem("consultor recusou")

    assert (ciclo.estado, ciclo.consultor_id) == ("EM_TRIAGEM_MANUAL", None)


def test_reabrir_um_chamado_resolvido_volta_para_o_roteamento():
    ciclo = CicloDeVidaDoChamado("t1")
    ciclo.iniciar_roteamento()
    ciclo.atribuir("ana")
    ciclo.iniciar_atendimento()
    ciclo.resolver()

    ciclo.reabrir()

    assert (ciclo.estado, ciclo.consultor_id) == ("EM_ROTEAMENTO", None)
    assert ciclo.aceita_roteamento


@pytest.mark.parametrize(
    ("preparar", "acao"),
    [
        ([], lambda c: c.atribuir("ana")),  # REGISTRADO não atribui sem rotear
        ([], lambda c: c.resolver()),
        (["iniciar_roteamento"], lambda c: c.fechar()),
        (["iniciar_roteamento", ("atribuir", "ana")], lambda c: c.resolver()),
    ],
)
def test_transicao_invalida_e_recusada(preparar, acao):
    ciclo = CicloDeVidaDoChamado("t1")
    for passo in preparar:
        if isinstance(passo, tuple):
            getattr(ciclo, passo[0])(*passo[1:])
        else:
            getattr(ciclo, passo)()

    with pytest.raises(TransicaoInvalidaError):
        acao(ciclo)


def test_estados_finais_nao_aceitam_mais_nada():
    ciclo = CicloDeVidaDoChamado("t1")
    ciclo.cancelar("loja desistiu")

    assert ciclo.final
    for acao in (
        lambda c: c.iniciar_roteamento(),
        lambda c: c.atribuir("ana"),
        lambda c: c.cancelar("de novo"),
        lambda c: c.reabrir(),
    ):
        with pytest.raises(TransicaoInvalidaError):
            acao(ciclo)


def test_restaurar_recria_o_estado_gravado():
    ciclo = CicloDeVidaDoChamado.restaurar("t1", "ATRIBUIDO", "ana", [("ATRIBUIDO", "ana")])

    ciclo.iniciar_atendimento()

    assert ciclo.estado == "EM_ATENDIMENTO"
