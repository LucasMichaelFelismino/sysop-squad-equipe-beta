"""Motor de Roteamento: a regra de negócio estável do sistema (Core Domain)."""

from __future__ import annotations

from datetime import timedelta

from sysop_squad.dominio.modelo import Chamado, Resultado
from sysop_squad.dominio.portas import (
    EstrategiaDeSelecao,
    ProvedorDeRotas,
    RegistroDeDisponibilidade,
    RepositorioDeConsultores,
    RotearChamado,
)

RAIO_KM = 50.0
TTL_RESERVA = timedelta(minutes=5)


class MotorDeRoteamento(RotearChamado):
    """Escolhe o consultor por localização, habilidade e disponibilidade.

    Recebe as portas e a estratégia pelo construtor (DIP): não instancia adaptador nem lê
    configuração. Não decide sobre retry: se uma dependência falha, a falha sobe como
    RoteamentoIndisponivelError e o consumidor aplica a Política de Retry (ADR 010).
    """

    def __init__(
        self,
        consultores: RepositorioDeConsultores,
        disponibilidade: RegistroDeDisponibilidade,
        rotas: ProvedorDeRotas,
        estrategia: EstrategiaDeSelecao,
        raio_km: float = RAIO_KM,
        ttl_reserva: timedelta = TTL_RESERVA,
    ) -> None:
        self._consultores = consultores
        self._disponibilidade = disponibilidade
        self._rotas = rotas
        self._estrategia = estrategia
        self._raio_km = raio_km
        self._ttl_reserva = ttl_reserva

    def executar(self, chamado: Chamado) -> Resultado:
        candidatos = self._consultores.buscar_candidatos(
            chamado.localizacao, self._raio_km, chamado.habilidades_exigidas
        )
        if not candidatos:
            return Resultado.triagem_manual("nenhum consultor elegível no raio")

        opcoes = [(c, self._rotas.estimar(c.posicao, chamado.localizacao)) for c in candidatos]

        for candidato, eta in self._estrategia.ordenar(opcoes):
            reserva = self._disponibilidade.reservar(candidato.id, chamado.id, self._ttl_reserva)
            if reserva is not None:
                return Resultado.atribuido(candidato.id, eta)

        return Resultado.triagem_manual("todos os candidatos estão ocupados")
