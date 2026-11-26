"""Modelo do Roteamento (Core Domain): chamado, consultor candidato, reserva e resultado."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

# (latitude, longitude) em graus decimais.
Coordenada = tuple[float, float]

PRIORIDADES = ("baixa", "normal", "alta", "critica")


@dataclass(frozen=True)
class Chamado:
    """Visão do chamado que o roteamento precisa (contrato interno canônico)."""

    id: str
    loja_id: str
    localizacao: Coordenada
    habilidades_exigidas: frozenset[str]
    prioridade: str = "normal"
    categoria: str = ""
    descricao: str = ""

    def __post_init__(self) -> None:
        lat, lon = self.localizacao
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"localização fora do intervalo: {lat}, {lon}")
        if self.prioridade not in PRIORIDADES:
            raise ValueError(f"prioridade inválida: {self.prioridade!r}")

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "loja_id": self.loja_id,
            "localizacao": list(self.localizacao),
            "habilidades_exigidas": sorted(self.habilidades_exigidas),
            "prioridade": self.prioridade,
            "categoria": self.categoria,
            "descricao": self.descricao,
        }

    @classmethod
    def de_dict(cls, dados: dict) -> Chamado:
        """Lê o contrato interno publicado no broker. Levanta KeyError/ValueError se inválido."""
        lat, lon = (float(valor) for valor in dados["localizacao"])
        habilidades = dados.get("habilidades_exigidas", [])
        if isinstance(habilidades, str):
            raise ValueError("habilidades_exigidas deve ser uma lista")
        return cls(
            id=str(dados["id"]),
            loja_id=str(dados["loja_id"]),
            localizacao=(lat, lon),
            habilidades_exigidas=frozenset(str(h) for h in habilidades),
            prioridade=str(dados.get("prioridade", "normal")),
            categoria=str(dados.get("categoria", "")),
            descricao=str(dados.get("descricao", "")),
        )


@dataclass(frozen=True)
class ConsultorCandidato:
    id: str
    posicao: Coordenada
    habilidades: frozenset[str]


@dataclass(frozen=True)
class Reserva:
    consultor_id: str
    chamado_id: str


@dataclass(frozen=True)
class Resultado:
    status: Literal["ATRIBUIDO", "TRIAGEM_MANUAL"]
    consultor_id: str | None = None
    eta: timedelta | None = None
    motivo: str | None = None

    @classmethod
    def atribuido(cls, consultor_id: str, eta: timedelta) -> Resultado:
        return cls("ATRIBUIDO", consultor_id=consultor_id, eta=eta)

    @classmethod
    def triagem_manual(cls, motivo: str) -> Resultado:
        return cls("TRIAGEM_MANUAL", motivo=motivo)
