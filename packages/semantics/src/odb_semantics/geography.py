"""Níveis territoriais oficiais do Brasil, do mais agregado ao mais detalhado (§13).

A árvore principal é Brasil → Grande Região → UF → Região Geográfica
Intermediária → Região Geográfica Imediata → Município (divisão regional do
IBGE de 2017). Os identificadores são internos: a correspondência com códigos
de nível de cada fonte fica no modelo de cada fonte.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeographyLevel:
    """Nível da hierarquia territorial principal."""

    id: str
    rank: int
    name: str


LEVELS: tuple[GeographyLevel, ...] = (
    GeographyLevel("brasil", 1, "Brasil"),
    GeographyLevel("regiao", 2, "Grande Região"),
    GeographyLevel("uf", 3, "Unidade da Federação"),
    GeographyLevel("regiao_intermediaria", 4, "Região Geográfica Intermediária"),
    GeographyLevel("regiao_imediata", 5, "Região Geográfica Imediata"),
    GeographyLevel("municipio", 6, "Município"),
)
LEVELS_BY_ID = {level.id: level for level in LEVELS}


def level_rank(level_id: str) -> int:
    """Posição do nível (1 = Brasil). Nível desconhecido gera ``ValueError``."""
    try:
        return LEVELS_BY_ID[level_id].rank
    except KeyError:
        msg = f"nível territorial desconhecido: {level_id!r} (válidos: {list(LEVELS_BY_ID)})"
        raise ValueError(msg) from None


def geography_key(level_id: str, code: str) -> str:
    """Chave determinística de território (``municipio:5101837``)."""
    level_rank(level_id)
    return f"{level_id}:{code}"
