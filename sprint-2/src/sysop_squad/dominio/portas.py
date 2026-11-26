"""Portas do domínio: o domínio declara o que precisa, sem citar tecnologia (ADR 004).

Cada porta isola uma barreira do C4 Nível 2:

- RepositorioDeConsultores  -> Banco Geoespacial (PostgreSQL/PostGIS, ADR 003)
- RegistroDeDisponibilidade -> Cache de disponibilidade (Redis, ADR 003)
- ProvedorDeRotas           -> API de Mapas (terceiro, via HTTP)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta

from sysop_squad.dominio.modelo import ConsultorCandidato, Coordenada, Reserva


class RepositorioDeConsultores(ABC):
    @abstractmethod
    def buscar_candidatos(
        self, origem: Coordenada, raio_km: float, habilidades: frozenset[str]
    ) -> list[ConsultorCandidato]:
        """Consultores elegíveis, do mais próximo ao mais distante."""


class RegistroDeDisponibilidade(ABC):
    @abstractmethod
    def reservar(self, consultor_id: str, chamado_id: str, ttl: timedelta) -> Reserva | None:
        """Reserva atômica: devolve None se o consultor já está reservado."""

    @abstractmethod
    def liberar(self, reserva: Reserva) -> None:
        """Desfaz a reserva. Não faz nada se ela expirou ou já pertence a outro chamado."""


class ProvedorDeRotas(ABC):
    @abstractmethod
    def estimar(self, origem: Coordenada, destino: Coordenada) -> timedelta:
        """Tempo de deslocamento. Levanta RoteamentoIndisponivelError se não houver estimativa."""
