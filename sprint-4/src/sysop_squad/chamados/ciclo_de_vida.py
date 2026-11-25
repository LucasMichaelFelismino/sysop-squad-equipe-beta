"""Ciclo de vida do chamado com o padrão State (GoF) - ADR 012.

    REGISTRADO ──► EM_ROTEAMENTO ──► ATRIBUIDO ──► EM_ATENDIMENTO ──► RESOLVIDO ──► FECHADO
        │               │   ▲            │                                │
        │               ▼   └────────────┼──────── reabrir ───────────────┘
        └──────► EM_TRIAGEM_MANUAL ◄─────┘ (consultor não pôde atender)
                        │
                        └──► ATRIBUIDO (operador atribui)

    REGISTRADO, EM_ROTEAMENTO, EM_TRIAGEM_MANUAL e ATRIBUIDO podem ir para CANCELADO.
    FECHADO e CANCELADO são finais.

Cada estado é uma classe que só implementa as transições permitidas; as demais herdam
o comportamento padrão de EstadoDoChamado, que levanta TransicaoInvalidaError. Isso
elimina os if/else sobre o status espalhados pelo código.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TransicaoInvalidaError(Exception):
    """A ação pedida não é permitida no estado atual do chamado."""


class EstadoDoChamado(ABC):
    @property
    @abstractmethod
    def nome(self) -> str: ...

    aceita_roteamento = False
    final = False

    def iniciar_roteamento(self, ciclo: CicloDeVidaDoChamado) -> None:
        self._recusar("iniciar o roteamento")

    def atribuir(self, ciclo: CicloDeVidaDoChamado, consultor_id: str) -> None:
        self._recusar("atribuir")

    def encaminhar_para_triagem(self, ciclo: CicloDeVidaDoChamado, motivo: str) -> None:
        self._recusar("encaminhar para triagem")

    def iniciar_atendimento(self, ciclo: CicloDeVidaDoChamado) -> None:
        self._recusar("iniciar o atendimento de")

    def resolver(self, ciclo: CicloDeVidaDoChamado) -> None:
        self._recusar("resolver")

    def fechar(self, ciclo: CicloDeVidaDoChamado) -> None:
        self._recusar("fechar")

    def reabrir(self, ciclo: CicloDeVidaDoChamado) -> None:
        self._recusar("reabrir")

    def cancelar(self, ciclo: CicloDeVidaDoChamado, motivo: str) -> None:
        self._recusar("cancelar")

    def _recusar(self, acao: str) -> None:
        raise TransicaoInvalidaError(f"não é possível {acao} um chamado {self.nome}")


class Registrado(EstadoDoChamado):
    nome = "REGISTRADO"
    aceita_roteamento = True

    def iniciar_roteamento(self, ciclo):
        ciclo._mudar_para(EmRoteamento())

    def encaminhar_para_triagem(self, ciclo, motivo):
        ciclo._mudar_para(EmTriagemManual(), motivo)

    def cancelar(self, ciclo, motivo):
        ciclo._mudar_para(Cancelado(), motivo)


class EmRoteamento(EstadoDoChamado):
    nome = "EM_ROTEAMENTO"
    aceita_roteamento = True

    def iniciar_roteamento(self, ciclo):
        pass  # nova tentativa vinda da fila de espera (retry): continua no mesmo estado

    def atribuir(self, ciclo, consultor_id):
        ciclo.consultor_id = consultor_id
        ciclo._mudar_para(Atribuido(), consultor_id)

    def encaminhar_para_triagem(self, ciclo, motivo):
        ciclo._mudar_para(EmTriagemManual(), motivo)

    def cancelar(self, ciclo, motivo):
        ciclo._mudar_para(Cancelado(), motivo)


class EmTriagemManual(EstadoDoChamado):
    nome = "EM_TRIAGEM_MANUAL"

    def atribuir(self, ciclo, consultor_id):
        ciclo.consultor_id = consultor_id
        ciclo._mudar_para(Atribuido(), consultor_id)

    def cancelar(self, ciclo, motivo):
        ciclo._mudar_para(Cancelado(), motivo)


class Atribuido(EstadoDoChamado):
    nome = "ATRIBUIDO"

    def iniciar_atendimento(self, ciclo):
        ciclo._mudar_para(EmAtendimento())

    def encaminhar_para_triagem(self, ciclo, motivo):
        ciclo.consultor_id = None
        ciclo._mudar_para(EmTriagemManual(), motivo)

    def cancelar(self, ciclo, motivo):
        ciclo._mudar_para(Cancelado(), motivo)


class EmAtendimento(EstadoDoChamado):
    nome = "EM_ATENDIMENTO"

    def resolver(self, ciclo):
        ciclo._mudar_para(Resolvido())


class Resolvido(EstadoDoChamado):
    nome = "RESOLVIDO"

    def fechar(self, ciclo):
        ciclo._mudar_para(Fechado())

    def reabrir(self, ciclo):
        ciclo.consultor_id = None
        ciclo._mudar_para(EmRoteamento(), "reaberto pela loja")


class Fechado(EstadoDoChamado):
    nome = "FECHADO"
    final = True


class Cancelado(EstadoDoChamado):
    nome = "CANCELADO"
    final = True


ESTADOS: dict[str, type[EstadoDoChamado]] = {
    estado.nome: estado
    for estado in (
        Registrado,
        EmRoteamento,
        EmTriagemManual,
        Atribuido,
        EmAtendimento,
        Resolvido,
        Fechado,
        Cancelado,
    )
}


class CicloDeVidaDoChamado:
    """Contexto do padrão State: guarda o estado atual e delega a ele cada ação."""

    def __init__(
        self,
        chamado_id: str,
        estado: EstadoDoChamado | None = None,
        consultor_id: str | None = None,
        historico: list[tuple[str, str]] | None = None,
    ) -> None:
        self.chamado_id = chamado_id
        self._estado = estado or Registrado()
        self.consultor_id = consultor_id
        self.historico: list[tuple[str, str]] = list(historico or [(self._estado.nome, "")])

    @classmethod
    def restaurar(
        cls,
        chamado_id: str,
        nome_do_estado: str,
        consultor_id: str | None = None,
        historico: list[tuple[str, str]] | None = None,
    ) -> CicloDeVidaDoChamado:
        """Recria o ciclo a partir do que foi gravado no banco."""
        return cls(chamado_id, ESTADOS[nome_do_estado](), consultor_id, historico)

    @property
    def estado(self) -> str:
        return self._estado.nome

    @property
    def aceita_roteamento(self) -> bool:
        return self._estado.aceita_roteamento

    @property
    def final(self) -> bool:
        return self._estado.final

    def iniciar_roteamento(self) -> None:
        self._estado.iniciar_roteamento(self)

    def atribuir(self, consultor_id: str) -> None:
        self._estado.atribuir(self, consultor_id)

    def encaminhar_para_triagem(self, motivo: str) -> None:
        self._estado.encaminhar_para_triagem(self, motivo)

    def iniciar_atendimento(self) -> None:
        self._estado.iniciar_atendimento(self)

    def resolver(self) -> None:
        self._estado.resolver(self)

    def fechar(self) -> None:
        self._estado.fechar(self)

    def reabrir(self) -> None:
        self._estado.reabrir(self)

    def cancelar(self, motivo: str) -> None:
        self._estado.cancelar(self, motivo)

    def _mudar_para(self, novo: EstadoDoChamado, detalhe: str = "") -> None:
        self._estado = novo
        self.historico.append((novo.nome, detalhe))
