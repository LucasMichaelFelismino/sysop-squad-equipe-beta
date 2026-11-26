"""Adaptador do repositório de chamados (PostgreSQL - ADR 006 da Sprint 3). Esquema em sql/schema.sql."""

from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from sysop_squad.chamados.ciclo_de_vida import CicloDeVidaDoChamado
from sysop_squad.chamados.portas import RepositorioDeChamados

SQL_REGISTRAR = """
INSERT INTO chamados (id, id_externo, estado, consultor_id, dados, historico)
VALUES (%(id)s, %(id_externo)s, %(estado)s, %(consultor_id)s, %(dados)s, %(historico)s)
ON CONFLICT (id_externo) DO NOTHING
RETURNING id
"""

SQL_OBTER = "SELECT estado, consultor_id, historico FROM chamados WHERE id = %(id)s"

SQL_SALVAR = """
UPDATE chamados
   SET estado = %(estado)s, consultor_id = %(consultor_id)s,
       historico = %(historico)s, atualizado_em = now()
 WHERE id = %(id)s
"""

SQL_DESCARTAR = "DELETE FROM chamados WHERE id = %(id)s"


class ChamadosPostgresAdapter(RepositorioDeChamados):
    def __init__(self, conexao: psycopg.Connection) -> None:
        self._conexao = conexao

    def registrar(self, id_externo: str, ciclo: CicloDeVidaDoChamado, dados: dict) -> bool:
        with self._conexao.cursor() as cursor:
            cursor.execute(
                SQL_REGISTRAR,
                {
                    "id": ciclo.chamado_id,
                    "id_externo": id_externo,
                    "estado": ciclo.estado,
                    "consultor_id": ciclo.consultor_id,
                    "dados": Jsonb(dados),
                    "historico": Jsonb(ciclo.historico),
                },
            )
            return cursor.fetchone() is not None

    def descartar(self, chamado_id: str) -> None:
        with self._conexao.cursor() as cursor:
            cursor.execute(SQL_DESCARTAR, {"id": chamado_id})

    def obter(self, chamado_id: str) -> CicloDeVidaDoChamado | None:
        with self._conexao.cursor() as cursor:
            cursor.execute(SQL_OBTER, {"id": chamado_id})
            linha = cursor.fetchone()
        if linha is None:
            return None
        estado, consultor_id, historico = linha
        return CicloDeVidaDoChamado.restaurar(
            chamado_id, estado, consultor_id, [tuple(item) for item in historico]
        )

    def salvar(self, ciclo: CicloDeVidaDoChamado) -> None:
        with self._conexao.cursor() as cursor:
            cursor.execute(
                SQL_SALVAR,
                {
                    "id": ciclo.chamado_id,
                    "estado": ciclo.estado,
                    "consultor_id": ciclo.consultor_id,
                    "historico": Jsonb(ciclo.historico),
                },
            )
