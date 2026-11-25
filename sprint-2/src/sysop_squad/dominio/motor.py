"""Motor de Roteamento: a regra de negócio estável do sistema."""

from __future__ import annotations

from datetime import timedelta

from sysop_squad.dominio.erros import RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import Chamado, Resultado
from sysop_squad.dominio.portas import (
    ProvedorDeRotas,
    RegistroDeDisponibilidade,
    RepositorioDeConsultores,
)

RAIO_KM = 50.0
TTL_RESERVA = timedelta(minutes=5)


class MotorDeRoteamento:
    """Escolhe o consultor por localização, habilidade e disponibilidade.

    Recebe as portas pelo construtor (DIP): não instancia adaptador nem lê configuração.
    """

    def __init__(
        self,
        consultores: RepositorioDeConsultores,
        disponibilidade: RegistroDeDisponibilidade,
        rotas: ProvedorDeRotas,
        raio_km: float = RAIO_KM,
        ttl_reserva: timedelta = TTL_RESERVA,
    ) -> None:
        self._consultores = consultores
        self._disponibilidade = disponibilidade
        self._rotas = rotas
        self._raio_km = raio_km
        self._ttl_reserva = ttl_reserva

    def executar(self, chamado: Chamado) -> Resultado:
        try:
            candidatos = self._consultores.buscar_candidatos(
                chamado.localizacao, self._raio_km, chamado.habilidades_exigidas
            )
            if not candidatos:
                return Resultado.triagem_manual("nenhum consultor elegível no raio")

            # Ordena pelo menor tempo de deslocamento, não pela distância em linha reta.
            ordenados = sorted(
                ((c, self._rotas.estimar(c.posicao, chamado.localizacao)) for c in candidatos),
                key=lambda par: par[1],
            )

            for candidato, eta in ordenados:
                reserva = self._disponibilidade.reservar(
                    candidato.id, chamado.id, self._ttl_reserva
                )
                if reserva is not None:
                    return Resultado.atribuido(candidato.id, eta)
        except RoteamentoIndisponivelError as erro:
            # Driver P2: perder sofisticação antes de perder a função essencial.
            return Resultado.triagem_manual(f"roteamento indisponível: {erro}")

        return Resultado.triagem_manual("todos os candidatos estão ocupados")
