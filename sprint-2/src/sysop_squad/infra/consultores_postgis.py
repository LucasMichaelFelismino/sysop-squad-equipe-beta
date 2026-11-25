"""Adaptador do Banco Geoespacial (PostgreSQL/PostGIS - ADR 003)."""

from __future__ import annotations

import psycopg

from sysop_squad.dominio.erros import RoteamentoIndisponivelError
from sysop_squad.dominio.modelo import ConsultorCandidato, Coordenada
from sysop_squad.dominio.portas import RepositorioDeConsultores

# consultores(id text, ativo bool, habilidades text[], posicao geography(Point, 4326))
SQL_CANDIDATOS = """
SELECT c.id,
       ST_Y(c.posicao::geometry) AS lat,
       ST_X(c.posicao::geometry) AS lon,
       c.habilidades
  FROM consultores AS c
 WHERE c.ativo
   AND c.habilidades @> %(habilidades)s
   AND ST_DWithin(
         c.posicao,
         ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
         %(raio_m)s)
 ORDER BY ST_Distance(
         c.posicao,
         ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography)
"""


class ConsultoresPostGISAdapter(RepositorioDeConsultores):
    def __init__(self, conexao: psycopg.Connection) -> None:
        self._conexao = conexao

    def buscar_candidatos(
        self, origem: Coordenada, raio_km: float, habilidades: frozenset[str]
    ) -> list[ConsultorCandidato]:
        lat, lon = origem
        parametros = {
            "lat": lat,
            "lon": lon,
            "raio_m": raio_km * 1000,
            "habilidades": sorted(habilidades),
        }
        try:
            with self._conexao.cursor() as cursor:
                cursor.execute(SQL_CANDIDATOS, parametros)
                linhas = cursor.fetchall()
        except psycopg.Error as erro:
            raise RoteamentoIndisponivelError("banco geoespacial indisponível") from erro

        return [
            ConsultorCandidato(id=str(id_), posicao=(lat_, lon_), habilidades=frozenset(hab))
            for id_, lat_, lon_, hab in linhas
        ]
