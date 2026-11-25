"""Servidor HTTP mínimo (WSGI, só biblioteca padrão) para POST /chamados.

Em produção fica atrás do API Gateway (Kong - ADR 005 da Sprint 3), que cuida de TLS,
JWT e rate limiting.
"""

from __future__ import annotations

import json
from http import HTTPStatus

from sysop_squad.apresentacao.api import RecepcaoDeChamadosAPI


def criar_aplicacao_wsgi(api: RecepcaoDeChamadosAPI):
    def responder(start_response, status: int, corpo: dict):
        start_response(
            f"{status} {HTTPStatus(status).phrase}",
            [("Content-Type", "application/json; charset=utf-8")],
        )
        return [json.dumps(corpo, ensure_ascii=False).encode("utf-8")]

    def aplicacao(environ, start_response):
        if environ.get("PATH_INFO") != "/chamados":
            return responder(start_response, 404, {"erro": "rota não encontrada"})
        if environ.get("REQUEST_METHOD") != "POST":
            return responder(start_response, 405, {"erro": "use POST"})
        try:
            tamanho = int(environ.get("CONTENT_LENGTH") or 0)
            corpo = json.loads(environ["wsgi.input"].read(tamanho) or b"null")
        except ValueError:
            return responder(start_response, 400, {"erro": "corpo não é JSON válido"})
        status, resposta = api.registrar(corpo)
        return responder(start_response, status, resposta)

    return aplicacao
