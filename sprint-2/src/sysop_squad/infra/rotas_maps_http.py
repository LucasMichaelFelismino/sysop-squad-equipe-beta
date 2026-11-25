"""Adaptador da API de Mapas (terceiro, via HTTP).

Usa o formato do OSRM (Open Source Routing Machine):
GET /route/v1/driving/{lon},{lat};{lon},{lat}?overview=false
"""

from __future__ import annotations

from datetime import timedelta

import httpx

from sysop_squad.dominio.erros import RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import Coordenada
from sysop_squad.dominio.portas import ProvedorDeRotas


class MapsHTTPAdapter(ProvedorDeRotas):
    """O timeout fica no cliente HTTP (composição), não na regra (ADR 004)."""

    def __init__(self, cliente: httpx.Client) -> None:
        self._cliente = cliente

    def estimar(self, origem: Coordenada, destino: Coordenada) -> timedelta:
        (lat_o, lon_o), (lat_d, lon_d) = origem, destino
        try:
            resposta = self._cliente.get(
                f"/route/v1/driving/{lon_o},{lat_o};{lon_d},{lat_d}",
                params={"overview": "false"},
            )
            resposta.raise_for_status()
            dados = resposta.json()
            if dados.get("code") != "Ok":
                raise ValueError(f"API de Mapas respondeu {dados.get('code')!r}")
            segundos = float(dados["routes"][0]["duration"])
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as erro:
            raise RoteamentoIndisponivelError("API de Mapas sem estimativa") from erro
        return timedelta(seconds=segundos)
