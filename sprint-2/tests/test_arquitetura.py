"""Fitness functions: as regras do ADR 004 e as invariantes do ADR 005 viram testes."""

import ast
import sys
from pathlib import Path

import pytest

import metricas

RAIZ = Path(__file__).resolve().parents[1] / "src" / "sysop_squad"


def _arvore(arquivo: Path) -> ast.Module:
    return ast.parse(arquivo.read_text(encoding="utf-8"))


def _imports(arquivo: Path):
    for no in ast.walk(_arvore(arquivo)):
        if isinstance(no, ast.Import):
            yield from (alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            yield "." * no.level + (no.module or "")


def test_dominio_so_importa_biblioteca_padrao_e_o_proprio_dominio():
    """ADR 004: o domínio não importa psycopg, redis, httpx, pika, infra nem apresentação."""
    violacoes = [
        f"{arquivo.name} importa {modulo}"
        for arquivo in sorted((RAIZ / "dominio").glob("*.py"))
        for modulo in _imports(arquivo)
        if not (
            modulo.startswith("sysop_squad.dominio")
            or modulo.split(".")[0] in sys.stdlib_module_names
        )
    ]
    assert violacoes == []


def test_todo_adaptador_de_infra_implementa_uma_porta_do_dominio():
    portas = {
        no.name for no in _arvore(RAIZ / "dominio" / "portas.py").body if isinstance(no, ast.ClassDef)
    }
    sem_porta = [
        no.name
        for arquivo in sorted((RAIZ / "infra").glob("*.py"))
        for no in _arvore(arquivo).body
        if isinstance(no, ast.ClassDef)
        and not portas & {b.id for b in no.bases if isinstance(b, ast.Name)}
    ]
    assert sem_porta == []


def test_dominio_tem_ce_zero_e_instabilidade_zero():
    """ADR 005, invariante 1."""
    dominio = metricas.analisar()[0]["dominio"]

    assert dominio.ce == 0
    assert dominio.instabilidade == 0


def test_dependencias_apontam_para_pacotes_mais_estaveis():
    """ADR 005, invariante 2 (Princípio das Dependências Estáveis)."""
    pacotes, dependencias = metricas.analisar()
    violacoes = [
        (origem, destino)
        for origem, destino in dependencias
        if pacotes[destino].instabilidade > pacotes[origem].instabilidade
    ]
    assert violacoes == []


def test_infra_so_e_instanciada_pela_composicao():
    """ADR 005: Ca de infra acima de 1 indica vazamento de tecnologia para o resto do sistema."""
    assert metricas.analisar()[0]["infra"].ca <= 1


@pytest.mark.xfail(
    strict=True,
    reason="ADR 005, invariante 3: falta extrair RotearChamado e FilaDeTriagemManual",
)
def test_distancia_do_dominio_cai_para_0_50():
    assert metricas.analisar()[0]["dominio"].distancia <= 0.50
