"""Strategy (ADR 009): trocar o critério de seleção sem mudar o MotorDeRoteamento."""

from datetime import timedelta

from dubles import ConsultoresEmMemoria, DisponibilidadeEmMemoria, RotasPorDistancia
from sysop_squad.dominio.estrategias import MenorTempoDeDeslocamento
from sysop_squad.dominio.modelo import Chamado, ConsultorCandidato
from sysop_squad.dominio.motor import MotorDeRoteamento
from sysop_squad.dominio.portas import EstrategiaDeSelecao

LOJA = (-19.9245, -43.9352)
ANA = ConsultorCandidato("ana", (-19.9300, -43.9400), frozenset({"pdv"}))
BRUNO = ConsultorCandidato("bruno", (-19.9600, -43.9600), frozenset({"pdv", "rede", "hardware"}))


class MaiorCompatibilidade(EstrategiaDeSelecao):
    """Estratégia alternativa, escrita só no teste, para provar que o motor não muda (OCP)."""

    def ordenar(self, opcoes):
        return sorted(opcoes, key=lambda opcao: (-len(opcao[0].habilidades), opcao[1]))


def _motor(estrategia):
    return MotorDeRoteamento(
        ConsultoresEmMemoria([ANA, BRUNO]), DisponibilidadeEmMemoria(), RotasPorDistancia(), estrategia
    )


def _chamado():
    return Chamado("t1", "loja-42", LOJA, frozenset({"pdv"}))


def test_menor_tempo_ordena_pelo_tempo_de_deslocamento():
    opcoes = [(BRUNO, timedelta(minutes=20)), (ANA, timedelta(minutes=5))]

    assert MenorTempoDeDeslocamento().ordenar(opcoes) == [
        (ANA, timedelta(minutes=5)),
        (BRUNO, timedelta(minutes=20)),
    ]


def test_menor_tempo_com_lista_vazia():
    assert MenorTempoDeDeslocamento().ordenar([]) == []


def test_trocar_a_estrategia_muda_a_escolha_sem_alterar_o_motor():
    assert _motor(MenorTempoDeDeslocamento()).executar(_chamado()).consultor_id == "ana"
    assert _motor(MaiorCompatibilidade()).executar(_chamado()).consultor_id == "bruno"
