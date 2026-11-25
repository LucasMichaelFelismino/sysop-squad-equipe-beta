"""Calcula Nc, Na, Ca, Ce, I, A e D dos pacotes do Sysop Squad (ADR 005).

Critério de contagem (o mesmo da Atividade de Validação Quantitativa):
- contam classes concretas, dataclasses de domínio e interfaces (abc.ABC);
- exceções de domínio (ex.: RoteamentoIndisponivelError) não entram na contagem;
- Ca e Ce contam classes distintas de outros pacotes, e não a quantidade de chamadas.

Uso:  python tools/metricas.py
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "src" / "sysop_squad"
PACOTES = ("dominio", "infra", "apresentacao")
BASES_DE_EXCECAO = {"Exception", "BaseException"}


@dataclass(frozen=True)
class _Classe:
    nome: str
    pacote: str
    bases: frozenset[str]
    referencias: frozenset[str]


@dataclass(frozen=True)
class MetricasDoPacote:
    pacote: str
    nc: int
    na: int
    ca: int
    ce: int

    @property
    def instabilidade(self) -> float:
        return self.ce / (self.ca + self.ce) if (self.ca + self.ce) else 0.0

    @property
    def abstracionalidade(self) -> float:
        return self.na / self.nc if self.nc else 0.0

    @property
    def distancia(self) -> float:
        return abs(self.abstracionalidade + self.instabilidade - 1)


def _nome(no: ast.expr) -> str:
    if isinstance(no, ast.Name):
        return no.id
    if isinstance(no, ast.Attribute):
        return no.attr
    return ""


def _ler_classes(raiz: Path) -> dict[str, _Classe]:
    classes: dict[str, _Classe] = {}
    for pacote in PACOTES:
        for arquivo in sorted((raiz / pacote).glob("*.py")):
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            for no in arvore.body:
                if not isinstance(no, ast.ClassDef):
                    continue
                nomes = {n.id for n in ast.walk(no) if isinstance(n, ast.Name)}
                nomes |= {n.attr for n in ast.walk(no) if isinstance(n, ast.Attribute)}
                classes[no.name] = _Classe(
                    nome=no.name,
                    pacote=pacote,
                    bases=frozenset(_nome(b) for b in no.bases),
                    referencias=frozenset(nomes - {no.name}),
                )
    return classes


def _sem_excecoes(classes: dict[str, _Classe]) -> dict[str, _Classe]:
    excecoes = set(BASES_DE_EXCECAO)
    mudou = True
    while mudou:  # herança transitiva: exceção de exceção também é exceção
        mudou = False
        for classe in classes.values():
            if classe.nome not in excecoes and classe.bases & excecoes:
                excecoes.add(classe.nome)
                mudou = True
    return {nome: c for nome, c in classes.items() if nome not in excecoes}


def analisar(raiz: Path = RAIZ) -> tuple[dict[str, MetricasDoPacote], set[tuple[str, str]]]:
    """Devolve as métricas por pacote e as dependências (origem, destino) entre pacotes."""
    classes = _sem_excecoes(_ler_classes(raiz))
    arestas = {
        (origem.nome, destino)
        for origem in classes.values()
        for destino in origem.referencias
        if destino in classes and classes[destino].pacote != origem.pacote
    }

    metricas = {}
    for pacote in PACOTES:
        do_pacote = [c for c in classes.values() if c.pacote == pacote]
        metricas[pacote] = MetricasDoPacote(
            pacote=pacote,
            nc=len(do_pacote),
            na=sum(1 for c in do_pacote if "ABC" in c.bases),
            ca=len({o for o, d in arestas if classes[d].pacote == pacote}),
            ce=len({d for o, d in arestas if classes[o].pacote == pacote}),
        )

    dependencias = {(classes[o].pacote, classes[d].pacote) for o, d in arestas}
    return metricas, dependencias


def _br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def main() -> None:
    metricas, dependencias = analisar()

    print("| Pacote | Nc | Na | Ca | Ce | I | A | D |")
    print("|---|---|---|---|---|---|---|---|")
    for m in metricas.values():
        print(
            f"| {m.pacote} | {m.nc} | {m.na} | {m.ca} | {m.ce} "
            f"| {_br(m.instabilidade)} | {_br(m.abstracionalidade)} | {_br(m.distancia)} |"
        )

    print("\nDependências entre pacotes (Princípio das Dependências Estáveis):")
    for origem, destino in sorted(dependencias):
        i_o, i_d = metricas[origem].instabilidade, metricas[destino].instabilidade
        situacao = "ok" if i_d <= i_o else "VIOLAÇÃO"
        print(f"  {origem} (I={_br(i_o)}) -> {destino} (I={_br(i_d)})  {situacao}")


if __name__ == "__main__":
    main()
