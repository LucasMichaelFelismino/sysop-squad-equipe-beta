"""API de Recepção: implementa o Contrato de Dados da Sprint 3 (POST /chamados).

Funciona como ACL de entrada (ADR 005 da Sprint 3): traduz o DTO público do OpenAPI
(idExterno, loja, incidente, prioridade...) para o Chamado interno, sem deixar o formato
externo vazar para o domínio.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pika

from sysop_squad.chamados.ciclo_de_vida import CicloDeVidaDoChamado
from sysop_squad.chamados.portas import RepositorioDeChamados
from sysop_squad.dominio.modelo import PRIORIDADES, Chamado
from sysop_squad.infra.mensageria import EXCHANGE_CHAMADOS, rota_de_entrada

TOLERANCIA_DE_RELOGIO = timedelta(minutes=5)


def _novo_id() -> str:
    return f"CH-{uuid.uuid4()}"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _texto(dados: dict, campo: str, maximo: int, obrigatorio: bool = True) -> str:
    valor = dados.get(campo)
    if valor is None and not obrigatorio:
        return ""
    if not isinstance(valor, str) or not 1 <= len(valor) <= maximo:
        raise ValueError(f"{campo} deve ser texto com 1 a {maximo} caracteres")
    return valor


def _numero(dados: dict, campo: str, minimo: float, maximo: float) -> float:
    valor = dados.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{campo} deve ser número")
    if not minimo <= valor <= maximo:
        raise ValueError(f"{campo} fora do intervalo [{minimo}, {maximo}]")
    return float(valor)


class RecepcaoDeChamadosAPI:
    """Valida o contrato, registra o chamado, publica no broker e responde 202.

    A resposta não espera o roteamento (ADR 000 e ADR 002): se o Motor de Roteamento
    estiver lento ou fora do ar, a loja continua abrindo chamados (Drivers P1 e P2).
    """

    def __init__(
        self,
        canal,
        chamados: RepositorioDeChamados,
        gerar_id: Callable[[], str] = _novo_id,
        agora: Callable[[], datetime] = _agora,
    ) -> None:
        self._canal = canal
        self._chamados = chamados
        self._gerar_id = gerar_id
        self._agora = agora

    def registrar(self, corpo: dict) -> tuple[int, dict]:
        try:
            id_externo, chamado, criado_em = self._traduzir(corpo)
        except (KeyError, TypeError, ValueError) as erro:
            return 400, {"erro": f"chamado inválido: {erro}"}

        if criado_em > self._agora() + TOLERANCIA_DE_RELOGIO:
            return 422, {"erro": "criadoEm está no futuro"}

        ciclo = CicloDeVidaDoChamado(chamado.id)
        dados = {**chamado.para_dict(), "id_externo": id_externo, "criado_em": criado_em.isoformat()}
        if not self._chamados.registrar(id_externo, ciclo, dados):
            return 409, {"erro": f"idExterno {id_externo} já registrado"}

        try:
            self._publicar(chamado)
        except Exception:
            # Sem confirmação do broker o chamado não foi aceito: libera o idExterno para reenvio.
            self._chamados.descartar(chamado.id)
            return 503, {"erro": "fila indisponível, tente novamente"}

        return 202, {
            "chamadoId": chamado.id,
            "status": "recebido",
            "mensagem": "Chamado recebido para roteamento.",
        }

    def _traduzir(self, corpo: dict) -> tuple[str, Chamado, datetime]:
        if not isinstance(corpo, dict):
            raise TypeError("o corpo deve ser um objeto JSON")
        loja = corpo["loja"]
        incidente = corpo["incidente"]
        if not isinstance(loja, dict) or not isinstance(incidente, dict):
            raise TypeError("loja e incidente devem ser objetos")

        prioridade = corpo["prioridade"]
        if prioridade not in PRIORIDADES:
            raise ValueError(f"prioridade deve ser uma de {', '.join(PRIORIDADES)}")

        habilidades = corpo.get("habilidadesNecessarias", [])
        if not isinstance(habilidades, list) or not all(isinstance(h, str) for h in habilidades):
            raise ValueError("habilidadesNecessarias deve ser uma lista de textos")
        if len(set(habilidades)) != len(habilidades):
            raise ValueError("habilidadesNecessarias não pode repetir itens")

        criado_em = datetime.fromisoformat(_texto(corpo, "criadoEm", 40))
        if criado_em.tzinfo is None:
            raise ValueError("criadoEm deve informar o fuso horário")

        chamado = Chamado(
            id=self._gerar_id(),
            loja_id=_texto(loja, "id", 100),
            localizacao=(
                _numero(loja, "latitude", -90, 90),
                _numero(loja, "longitude", -180, 180),
            ),
            habilidades_exigidas=frozenset(habilidades),
            prioridade=prioridade,
            categoria=_texto(incidente, "categoria", 100),
            descricao=_texto(incidente, "descricao", 2000),
        )
        return _texto(corpo, "idExterno", 100), chamado, criado_em

    def _publicar(self, chamado: Chamado) -> None:
        self._canal.basic_publish(
            exchange=EXCHANGE_CHAMADOS,
            routing_key=rota_de_entrada(chamado.prioridade),  # Content-Based Router
            body=json.dumps(chamado.para_dict(), ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # mensagem persistente
                message_id=chamado.id,  # chave de idempotência (ADR 000)
                correlation_id=chamado.id,
            ),
        )
