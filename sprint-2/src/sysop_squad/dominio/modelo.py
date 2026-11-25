"""Modelo do domínio: chamado, consultor candidato, reserva e resultado do roteamento."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

# (latitude, longitude) em graus decimais.
Coordenada = tuple[float, float]


@dataclass(frozen=True)
class Chamado:
    id: str
    loja_id: str
    localizacao: Coordenada
    habilidades_exigidas: frozenset[str]
    descricao: str = ""

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "loja_id": self.loja_id,
            "localizacao": list(self.localizacao),
            "habilidades_exigidas": sorted(self.habilidades_exigidas),
            "descricao": self.descricao,
        }

    @classmethod
    def de_dict(cls, dados: dict) -> Chamado:
        """Monta o chamado a partir do JSON. Levanta KeyError/ValueError se faltar dado."""
        lat, lon = (float(valor) for valor in dados["localizacao"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"localização fora do intervalo: {lat}, {lon}")

        habilidades = dados.get("habilidades_exigidas", [])
        if isinstance(habilidades, str):
            raise ValueError("habilidades_exigidas deve ser uma lista")

        return cls(
            id=str(dados["id"]),
            loja_id=str(dados["loja_id"]),
            localizacao=(lat, lon),
            habilidades_exigidas=frozenset(str(h) for h in habilidades),
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
