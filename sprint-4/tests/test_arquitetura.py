"""Fitness functions: regras de arquitetura viram testes (governança automatizada)."""

import ast
import sys
from pathlib import Path

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


def _violacoes(pacote: str):
    return [
        f"{arquivo.name} importa {modulo}"
        for arquivo in sorted((RAIZ / pacote).glob("*.py"))
        for modulo in _imports(arquivo)
        if not (
            modulo.startswith(f"sysop_squad.{pacote}")
            or modulo.split(".")[0] in sys.stdlib_module_names
        )
    ]


def test_regra_1_dominio_nao_referencia_infraestrutura():
    """O Core Domain só importa a biblioteca padrão e ele mesmo."""
    assert _violacoes("dominio") == []


def test_regra_1_gestao_de_chamados_nao_referencia_infraestrutura():
    assert _violacoes("chamados") == []


def test_regra_2_todo_adaptador_implementa_uma_porta():
    portas = {
        no.name
        for arquivo in (RAIZ / "dominio" / "portas.py", RAIZ / "chamados" / "portas.py")
        for no in _arvore(arquivo).body
        if isinstance(no, ast.ClassDef)
    }
    sem_porta = [
        no.name
        for arquivo in sorted((RAIZ / "infra").glob("*.py"))
        for no in _arvore(arquivo).body
        if isinstance(no, ast.ClassDef)
        and not portas & {b.id for b in no.bases if isinstance(b, ast.Name)}
    ]
    assert sem_porta == []


def test_invariante_1_dominio_tem_ce_zero():
    """ADR 005 da Sprint 2."""
    dominio = metricas.analisar()[0]["dominio"]

    assert (dominio.ce, dominio.instabilidade) == (0, 0)


def test_invariante_2_dependencias_apontam_para_pacotes_mais_estaveis():
    pacotes, dependencias = metricas.analisar()

    assert [
        (origem, destino)
        for origem, destino in dependencias
        if pacotes[destino].instabilidade > pacotes[origem].instabilidade
    ] == []


def test_invariante_3_distancia_do_dominio_caiu_para_0_50():
    """ADR 005 da Sprint 2: cumprida na Sprint 4 com a extração de RotearChamado e FilaDeTriagemManual."""
    assert metricas.analisar()[0]["dominio"].distancia <= 0.50


def test_infra_so_e_instanciada_pela_composicao():
    """Ca de infra acima de 1 indica vazamento de tecnologia para o resto do sistema."""
    assert metricas.analisar()[0]["infra"].ca <= 1
