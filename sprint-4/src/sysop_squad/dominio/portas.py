"""Portas do Roteamento: o domínio declara o que precisa, sem citar tecnologia.

Saída (implementadas na infra):
- RepositorioDeConsultores  -> Banco Geoespacial (PostgreSQL/PostGIS)
- RegistroDeDisponibilidade -> Cache de disponibilidade (Redis)
- ProvedorDeRotas           -> API de Mapas (HTTP), protegida por Circuit Breaker
- FilaDeTriagemManual       -> fila de triagem manual no RabbitMQ (Driver P2)

Entrada (implementada pelo motor, usada pelo consumidor da fila):
- RotearChamado

Estratégia (ADR 009 - Strategy):
- EstrategiaDeSelecao
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta

from sysop_squad.dominio.modelo import Chamado, ConsultorCandidato, Coordenada, Reserva, Resultado


class RepositorioDeConsultores(ABC):
    @abstractmethod
    def buscar_candidatos(
        self, origem: Coordenada, raio_km: float, habilidades: frozenset[str]
    ) -> list[ConsultorCandidato]:
        """Consultores elegíveis, do mais próximo ao mais distante."""


class RegistroDeDisponibilidade(ABC):
    @abstractmethod
    def reservar(self, consultor_id: str, chamado_id: str, ttl: timedelta) -> Reserva | None:
        """Reserva atômica: devolve None se o consultor já está reservado por OUTRO chamado.

        Reservar de novo para o mesmo chamado devolve a mesma reserva (reentrega da fila).
        """

    @abstractmethod
    def liberar(self, reserva: Reserva) -> None:
        """Desfaz a reserva. Não faz nada se ela expirou ou já pertence a outro chamado."""


class ProvedorDeRotas(ABC):
    @abstractmethod
    def estimar(self, origem: Coordenada, destino: Coordenada) -> timedelta:
        """Tempo de deslocamento. Levanta RoteamentoIndisponivelError se não houver estimativa."""


class RotearChamado(ABC):
    """Porta de entrada do roteamento (extraída conforme o ADR 005 da Sprint 2)."""

    @abstractmethod
    def executar(self, chamado: Chamado) -> Resultado:
        """Escolhe e reserva um consultor. Levanta RoteamentoIndisponivelError em falha transitória."""


class FilaDeTriagemManual(ABC):
    """Porta de saída para a triagem manual (extraída conforme o ADR 005 da Sprint 2)."""

    @abstractmethod
    def encaminhar(self, chamado: Chamado, motivo: str) -> None:
        """Entrega o chamado à equipe de triagem, com o motivo de não ter sido roteado."""


class EstrategiaDeSelecao(ABC):
    """Critério de ordenação dos candidatos (ADR 009 - Strategy)."""

    @abstractmethod
    def ordenar(
        self, opcoes: list[tuple[ConsultorCandidato, timedelta]]
    ) -> list[tuple[ConsultorCandidato, timedelta]]:
        """Devolve as opções (candidato, tempo de deslocamento) na ordem em que serão tentadas."""
