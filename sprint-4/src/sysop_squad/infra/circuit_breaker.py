"""Circuit Breaker na frente da API de Mapas (Política de Retry e Fallback, Sprint 3).

É um Proxy: implementa a mesma porta ProvedorDeRotas e repassa as chamadas ao adaptador
real enquanto o circuito está fechado.

    FECHADO ── N falhas seguidas ──► ABERTO ── passou o tempo de espera ──► MEIO_ABERTO
       ▲                                ▲                                      │
       └────────── chamada de teste deu certo ──────────── falhou de novo ─────┘
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import timedelta

from sysop_squad.dominio.erros import CircuitoAbertoError, RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import Coordenada
from sysop_squad.dominio.portas import ProvedorDeRotas

FECHADO = "FECHADO"
ABERTO = "ABERTO"
MEIO_ABERTO = "MEIO_ABERTO"


class CircuitBreakerDeRotas(ProvedorDeRotas):
    def __init__(
        self,
        provedor: ProvedorDeRotas,
        limite_de_falhas: int = 5,
        tempo_aberto: timedelta = timedelta(seconds=30),
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provedor = provedor
        self._limite_de_falhas = limite_de_falhas
        self._tempo_aberto = tempo_aberto.total_seconds()
        self._relogio = relogio
        self._estado = FECHADO
        self._falhas_seguidas = 0
        self._aberto_desde = 0.0
        self._trava = threading.Lock()

    @property
    def estado(self) -> str:
        return self._estado

    def estimar(self, origem: Coordenada, destino: Coordenada) -> timedelta:
        with self._trava:
            if self._estado == ABERTO:
                if self._relogio() - self._aberto_desde < self._tempo_aberto:
                    raise CircuitoAbertoError("circuito da API de Mapas está aberto")
                self._estado = MEIO_ABERTO  # deixa passar uma chamada de teste

        try:
            eta = self._provedor.estimar(origem, destino)
        except RoteamentoIndisponivelError:
            with self._trava:
                self._falhas_seguidas += 1
                if self._estado == MEIO_ABERTO or self._falhas_seguidas >= self._limite_de_falhas:
                    self._estado = ABERTO
                    self._aberto_desde = self._relogio()
            raise

        with self._trava:
            self._estado = FECHADO
            self._falhas_seguidas = 0
        return eta
