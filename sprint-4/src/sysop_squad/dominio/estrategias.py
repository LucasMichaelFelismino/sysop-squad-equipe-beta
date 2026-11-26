"""Estratégias de seleção de consultores (ADR 009 - Strategy).

Uma regra nova (por exemplo, priorizar quem tem mais habilidades em comum) vira uma
classe nova que implementa EstrategiaDeSelecao, sem alterar o MotorDeRoteamento (OCP).
"""

from __future__ import annotations

from sysop_squad.dominio.portas import EstrategiaDeSelecao


class MenorTempoDeDeslocamento(EstrategiaDeSelecao):
    """Tenta primeiro o consultor que chega mais rápido à loja."""

    def ordenar(self, opcoes):
        return sorted(opcoes, key=lambda opcao: opcao[1])
