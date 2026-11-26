"""Consumidor AMQP: roteia o chamado e aplica a Política de Retry e Fallback (ADR 010).

    falha transitória, ainda há tentativa ──► fila de espera (1 s, 2 s + jitter) ──► volta para a fila
    3ª falha ou circuito aberto ────────────► triagem manual (Driver P2)
    mensagem irrecuperável ─────────────────► nack sem requeue ──► DLQ
    chamado já atribuído/triado (reentrega) ► ack sem fazer nada (idempotência)
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Callable

import pika

from sysop_squad.chamados.portas import RepositorioDeChamados
from sysop_squad.dominio.erros import CircuitoAbertoError, RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import Chamado, Resultado
from sysop_squad.dominio.portas import FilaDeTriagemManual, RotearChamado
from sysop_squad.infra.mensageria import (
    CABECALHO_TENTATIVA,
    ESPERAS,
    EXCHANGE_CHAMADOS,
    FILA_ROTEAMENTO,
    FILA_ROTEAMENTO_PRIORITARIA,
    JITTER_MAXIMO,
    ROTA_ATRIBUIDO,
    TENTATIVAS_MAXIMAS,
    exchange_de_espera,
)

log = logging.getLogger(__name__)


class ConsumidorDeChamadosAMQP:
    def __init__(
        self,
        canal,
        rotear: RotearChamado,
        triagem: FilaDeTriagemManual,
        chamados: RepositorioDeChamados,
        sortear_jitter: Callable[[float, float], float] = random.uniform,
        prefetch: int = 10,
    ) -> None:
        self._canal = canal
        self._rotear = rotear
        self._triagem = triagem
        self._chamados = chamados
        self._sortear_jitter = sortear_jitter
        self._prefetch = prefetch

    def iniciar(self) -> None:
        self._canal.basic_qos(prefetch_count=self._prefetch)
        for fila in (FILA_ROTEAMENTO_PRIORITARIA, FILA_ROTEAMENTO):
            self._canal.basic_consume(queue=fila, on_message_callback=self.ao_receber)
        self._canal.start_consuming()

    def ao_receber(self, canal, metodo, propriedades, corpo: bytes) -> None:
        try:
            chamado = Chamado.de_dict(json.loads(corpo))
        except (KeyError, TypeError, ValueError):
            log.exception("Mensagem irrecuperável; enviando para a DLQ")
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return

        ciclo = self._chamados.obter(chamado.id)
        if ciclo is None:
            log.error("Chamado %s não está registrado; enviando para a DLQ", chamado.id)
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return
        if not ciclo.aceita_roteamento:
            canal.basic_ack(delivery_tag=metodo.delivery_tag)  # reentrega de algo já resolvido
            return

        tentativa = self._tentativa(propriedades)
        ciclo.iniciar_roteamento()
        try:
            resultado = self._rotear.executar(chamado)
        except CircuitoAbertoError as erro:
            resultado = Resultado.triagem_manual(f"API de Mapas indisponível ({erro})")
        except RoteamentoIndisponivelError as erro:
            if tentativa < TENTATIVAS_MAXIMAS:
                self._agendar_nova_tentativa(canal, metodo, chamado, corpo, tentativa)
                self._chamados.salvar(ciclo)
                canal.basic_ack(delivery_tag=metodo.delivery_tag)
                return
            resultado = Resultado.triagem_manual(
                f"roteamento indisponível após {tentativa} tentativas ({erro})"
            )
        except Exception:
            log.exception("Erro inesperado no roteamento do chamado %s; enviando para a DLQ", chamado.id)
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return

        if resultado.status == "ATRIBUIDO":
            ciclo.atribuir(resultado.consultor_id)
            self._publicar_atribuicao(canal, chamado, resultado)
        else:
            ciclo.encaminhar_para_triagem(resultado.motivo)
            self._triagem.encaminhar(chamado, resultado.motivo)

        self._chamados.salvar(ciclo)
        canal.basic_ack(delivery_tag=metodo.delivery_tag)

    @staticmethod
    def _tentativa(propriedades) -> int:
        cabecalhos = getattr(propriedades, "headers", None) or {}
        return int(cabecalhos.get(CABECALHO_TENTATIVA, 1))

    def _agendar_nova_tentativa(self, canal, metodo, chamado, corpo, tentativa) -> None:
        espera = ESPERAS[tentativa - 1].total_seconds()
        jitter = self._sortear_jitter(0.0, JITTER_MAXIMO.total_seconds())
        canal.basic_publish(
            exchange=exchange_de_espera(tentativa),
            routing_key=metodo.routing_key,  # ao expirar, volta para a mesma fila de roteamento
            body=corpo,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                expiration=str(int((espera + jitter) * 1000)),
                headers={CABECALHO_TENTATIVA: tentativa + 1},
                message_id=chamado.id,
                correlation_id=chamado.id,
            ),
        )
        log.warning("Chamado %s: tentativa %d falhou, nova tentativa agendada", chamado.id, tentativa)

    @staticmethod
    def _publicar_atribuicao(canal, chamado, resultado) -> None:
        evento = {
            "chamado_id": chamado.id,
            "consultor_id": resultado.consultor_id,
            "eta_segundos": resultado.eta.total_seconds(),
        }
        canal.basic_publish(
            exchange=EXCHANGE_CHAMADOS,
            routing_key=ROTA_ATRIBUIDO,
            body=json.dumps(evento).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=f"atribuicao-{chamado.id}",
                correlation_id=chamado.id,
            ),
        )
