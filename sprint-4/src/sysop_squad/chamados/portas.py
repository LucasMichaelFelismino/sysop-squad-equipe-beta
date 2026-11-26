"""Portas do módulo Gestão de Chamados."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sysop_squad.chamados.ciclo_de_vida import CicloDeVidaDoChamado


class RepositorioDeChamados(ABC):
    """Persistência dos chamados (PostgreSQL - ADR 006 da Sprint 3)."""

    @abstractmethod
    def registrar(self, id_externo: str, ciclo: CicloDeVidaDoChamado, dados: dict) -> bool:
        """Grava um chamado novo. Devolve False se o id_externo já existe (HTTP 409)."""

    @abstractmethod
    def descartar(self, chamado_id: str) -> None:
        """Apaga um registro que não chegou ao broker, para a loja poder reenviar."""

    @abstractmethod
    def obter(self, chamado_id: str) -> CicloDeVidaDoChamado | None:
        """Ciclo de vida do chamado, ou None se ele não existe."""

    @abstractmethod
    def salvar(self, ciclo: CicloDeVidaDoChamado) -> None:
        """Grava o estado atual e o histórico do ciclo de vida."""
