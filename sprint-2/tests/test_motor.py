"""Regra de roteamento testada com dublês em memória, sem banco, cache ou rede (ADR 004)."""

from datetime import timedelta

from dubles import (
    ConsultoresEmMemoria,
    DisponibilidadeEmMemoria,
    DisponibilidadeForaDoAr,
    RotasFixas,
    RotasForaDoAr,
    RotasPorDistancia,
)
from sysop_squad.dominio.modelo import Chamado, ConsultorCandidato
from sysop_squad.dominio.motor import MotorDeRoteamento

LOJA = (-19.9245, -43.9352)  # Belo Horizonte, centro
PERTO = (-19.9300, -43.9400)  # ~0,8 km da loja
MEDIO = (-19.9600, -43.9600)  # ~4,7 km da loja
LONGE = (-20.4000, -43.9352)  # ~53 km da loja, fora do raio de 50 km

ANA = ConsultorCandidato("ana", PERTO, frozenset({"pdv", "rede"}))
BRUNO = ConsultorCandidato("bruno", MEDIO, frozenset({"pdv"}))
CARLA = ConsultorCandidato("carla", PERTO, frozenset({"impressora"}))
DIEGO = ConsultorCandidato("diego", LONGE, frozenset({"pdv"}))

TTL = timedelta(minutes=5)


def chamado(id_="t1", habilidades=("pdv",)):
    return Chamado(
        id=id_, loja_id="loja-42", localizacao=LOJA, habilidades_exigidas=frozenset(habilidades)
    )


def motor(consultores=(ANA, BRUNO, CARLA, DIEGO), disponibilidade=None, rotas=None):
    return MotorDeRoteamento(
        ConsultoresEmMemoria(list(consultores)),
        disponibilidade or DisponibilidadeEmMemoria(),
        rotas or RotasPorDistancia(),
    )


def test_atribui_o_consultor_mais_proximo_com_a_habilidade():
    resultado = motor().executar(chamado())

    assert resultado.status == "ATRIBUIDO"
    assert resultado.consultor_id == "ana"
    assert resultado.eta > timedelta(0)


def test_ignora_consultor_sem_a_habilidade_exigida():
    resultado = motor().executar(chamado(habilidades=("impressora",)))

    assert resultado.consultor_id == "carla"


def test_ordena_pelo_tempo_de_deslocamento_e_nao_pela_distancia():
    transito = RotasFixas({PERTO: timedelta(minutes=40), MEDIO: timedelta(minutes=10)})

    resultado = motor(rotas=transito).executar(chamado())

    assert resultado.consultor_id == "bruno"
    assert resultado.eta == timedelta(minutes=10)


def test_pula_consultor_ja_reservado():
    disponibilidade = DisponibilidadeEmMemoria()
    disponibilidade.reservar("ana", "outro-chamado", TTL)

    resultado = motor(disponibilidade=disponibilidade).executar(chamado())

    assert resultado.consultor_id == "bruno"


def test_dois_chamados_nao_reservam_o_mesmo_consultor():
    """Driver P1: a reserva atômica impede atribuição dupla."""
    m = motor(consultores=(ANA,))

    primeiro = m.executar(chamado("t1"))
    segundo = m.executar(chamado("t2"))

    assert primeiro.consultor_id == "ana"
    assert segundo.status == "TRIAGEM_MANUAL"


def test_api_de_mapas_fora_do_ar_manda_para_triagem_manual():
    """Driver P2: a falha do roteamento não impede o chamado de seguir."""
    disponibilidade = DisponibilidadeEmMemoria()

    resultado = motor(disponibilidade=disponibilidade, rotas=RotasForaDoAr()).executar(chamado())

    assert resultado.status == "TRIAGEM_MANUAL"
    assert "indisponível" in resultado.motivo
    assert disponibilidade.reservar("ana", "outro", TTL) is not None  # ninguém ficou preso


def test_cache_fora_do_ar_manda_para_triagem_manual():
    resultado = motor(disponibilidade=DisponibilidadeForaDoAr()).executar(chamado())

    assert resultado.status == "TRIAGEM_MANUAL"


def test_sem_candidato_no_raio_vai_para_triagem_manual():
    resultado = motor(consultores=(DIEGO,)).executar(chamado())

    assert resultado.status == "TRIAGEM_MANUAL"
    assert resultado.motivo == "nenhum consultor elegível no raio"
