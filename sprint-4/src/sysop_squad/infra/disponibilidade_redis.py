"""Adaptador do Cache de disponibilidade (Redis - ADR 003 da Sprint 1)."""

from __future__ import annotations

from datetime import timedelta

import redis

from sysop_squad.dominio.erros import RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import Reserva
from sysop_squad.dominio.portas import RegistroDeDisponibilidade

PREFIXO = "consultor:"


def _texto(valor: bytes | str | None) -> str | None:
    return valor.decode("utf-8") if isinstance(valor, bytes) else valor


class DisponibilidadeRedisAdapter(RegistroDeDisponibilidade):
    """A reserva é um SET NX com expiração: só um chamado consegue gravar a chave."""

    def __init__(self, cliente: redis.Redis) -> None:
        self._cliente = cliente

    def reservar(self, consultor_id: str, chamado_id: str, ttl: timedelta) -> Reserva | None:
        chave = f"{PREFIXO}{consultor_id}"
        try:
            aceito = self._cliente.set(
                chave, str(chamado_id), nx=True, px=int(ttl.total_seconds() * 1000)
            )
            # Reentrega da mesma mensagem: a reserva já é deste chamado (idempotência).
            if not aceito and _texto(self._cliente.get(chave)) == str(chamado_id):
                aceito = True
        except redis.RedisError as erro:
            raise RoteamentoIndisponivelError("cache de disponibilidade indisponível") from erro
        return Reserva(consultor_id, chamado_id) if aceito else None

    def liberar(self, reserva: Reserva) -> None:
        chave = f"{PREFIXO}{reserva.consultor_id}"
        try:
            with self._cliente.pipeline() as pipe:
                # WATCH garante que só apagamos a chave se ela ainda for deste chamado.
                pipe.watch(chave)
                if _texto(pipe.get(chave)) != str(reserva.chamado_id):
                    return
                pipe.multi()
                pipe.delete(chave)
                pipe.execute()
        except redis.WatchError:
            return  # a chave mudou no meio: a reserva já não é deste chamado
        except redis.RedisError as erro:
            raise RoteamentoIndisponivelError("cache de disponibilidade indisponível") from erro
