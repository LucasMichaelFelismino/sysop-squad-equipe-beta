"""Servidor WSGI do POST /chamados."""

import io
import json

import pytest

pytest.importorskip("pika")

from dubles import CanalFalso, ChamadosEmMemoria  # noqa: E402
from sysop_squad.apresentacao.api import RecepcaoDeChamadosAPI  # noqa: E402
from sysop_squad.apresentacao.servidor_http import criar_aplicacao_wsgi  # noqa: E402
from test_api_contrato import AGORA, EXEMPLO  # noqa: E402


def _chamar(metodo, caminho, corpo=b""):
    app = criar_aplicacao_wsgi(
        RecepcaoDeChamadosAPI(CanalFalso(), ChamadosEmMemoria(), lambda: "CH-1", lambda: AGORA)
    )
    respostas = {}

    def start_response(status, cabecalhos):
        respostas["status"] = status

    environ = {
        "REQUEST_METHOD": metodo,
        "PATH_INFO": caminho,
        "CONTENT_LENGTH": str(len(corpo)),
        "wsgi.input": io.BytesIO(corpo),
    }
    corpo_resposta = b"".join(app(environ, start_response))
    return respostas["status"], json.loads(corpo_resposta)


def test_post_chamados_responde_202_accepted():
    status, corpo = _chamar("POST", "/chamados", json.dumps(EXEMPLO).encode())

    assert status == "202 Accepted"
    assert corpo["chamadoId"] == "CH-1"


def test_json_quebrado_da_400():
    assert _chamar("POST", "/chamados", b"{quebrado")[0] == "400 Bad Request"


def test_rota_e_metodo_errados():
    assert _chamar("POST", "/outra")[0] == "404 Not Found"
    assert _chamar("GET", "/chamados")[0] == "405 Method Not Allowed"
