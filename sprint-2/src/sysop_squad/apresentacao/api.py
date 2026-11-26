"""API de Recepção (contêiner "API Gateway / API de Recepção")."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

import pika

from sysop_squad.apresentacao.topologia import EXCHANGE_CHAMADOS, ROTA_ABERTO
from sysop_squad.dominio.modelo import Chamado


def _novo_id() -> str:
    return str(uuid.uuid4())


class RecepcaoDeChamadosAPI:
    """Valida o mínimo, publica o chamado no broker e responde 202 Accepted.

    A resposta não espera o roteamento (ADR 000 e ADR 002): se o Motor de Roteamento
    estiver lento ou fora do ar, a loja continua abrindo chamados (Drivers P1 e P2).
    Não depende de framework web: FastAPI ou Flask só precisam chamar `abrir`.
    """

    def __init__(self, canal, gerar_id: Callable[[], str] = _novo_id) -> None:
        self._canal = canal
        self._gerar_id = gerar_id

    def abrir(self, corpo: dict) -> tuple[int, dict]:
        try:
            chamado = Chamado.de_dict({**corpo, "id": self._gerar_id()})
        except (KeyError, TypeError, ValueError) as erro:
            return 400, {"erro": f"chamado inválido: {erro!r}"}

        self._canal.basic_publish(
            exchange=EXCHANGE_CHAMADOS,
            routing_key=ROTA_ABERTO,
            body=json.dumps(chamado.para_dict()).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # mensagem persistente
                message_id=chamado.id,  # chave de idempotência (ADR 000)
                correlation_id=chamado.id,
            ),
        )
        return 202, {"id": chamado.id, "status": "ACEITO"}
