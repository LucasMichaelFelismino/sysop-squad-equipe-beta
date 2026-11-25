"""Estimativa de rota sem API externa (usada com SYSOP_MAPAS=local - ADR 007)."""

from __future__ import annotations

import math
from datetime import timedelta

from sysop_squad.dominio.modelo import Coordenada
from sysop_squad.dominio.portas import ProvedorDeRotas

RAIO_DA_TERRA_KM = 6371.0


class RotasEstimadasPorDistancia(ProvedorDeRotas):
    """Tempo = distância em linha reta (haversine) dividida por uma velocidade média."""

    def __init__(self, velocidade_media_kmh: float = 30.0) -> None:
        self._velocidade_media_kmh = velocidade_media_kmh

    def estimar(self, origem: Coordenada, destino: Coordenada) -> timedelta:
        lat1, lon1, lat2, lon2 = map(math.radians, (*origem, *destino))
        h = (
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
        distancia_km = 2 * RAIO_DA_TERRA_KM * math.asin(math.sqrt(h))
        return timedelta(hours=distancia_km / self._velocidade_media_kmh)
