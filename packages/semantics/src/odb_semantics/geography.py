"""Níveis territoriais oficiais do Brasil (§13).

A árvore principal é Brasil → Grande Região → UF → Região Geográfica
Intermediária → Região Geográfica Imediata → Município (divisão regional do
IBGE de 2017).

Há também **recortes especiais**, que não cabem na árvore porque atravessam as
divisões administrativas: territórios quilombolas (um território pode estar em
duas UFs), terras indígenas, Coordenações Regionais da Funai e Amazônia
Legal (o Maranhão e o Mato Grosso estão só em parte).
Cada recorte tem um nível próprio e um nível de "parte por UF", que fica dentro
de uma UF e dentro do recorte. Por isso um nível pode ter mais de um nível
ancestral, e a hierarquia é um grafo, não uma árvore (``ANCESTOR_LEVELS``).

Os identificadores são internos. A correspondência com os códigos de nível de
cada fonte fica no modelo da fonte.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeographyLevel:
    """Nível territorial."""

    id: str
    rank: int
    name: str
    # Recorte especial (fora da árvore administrativa principal).
    special: bool = False


LEVELS: tuple[GeographyLevel, ...] = (
    GeographyLevel("brasil", 1, "Brasil"),
    GeographyLevel("regiao", 2, "Grande Região"),
    GeographyLevel("uf", 3, "Unidade da Federação"),
    GeographyLevel("regiao_intermediaria", 4, "Região Geográfica Intermediária"),
    GeographyLevel("regiao_imediata", 5, "Região Geográfica Imediata"),
    GeographyLevel("municipio", 6, "Município"),
    GeographyLevel("amazonia_legal", 7, "Amazônia Legal", special=True),
    GeographyLevel("amazonia_legal_uf", 8, "Amazônia Legal de Unidade da Federação", special=True),
    GeographyLevel("territorio_quilombola", 9, "Território Quilombola", special=True),
    GeographyLevel(
        "territorio_quilombola_uf",
        10,
        "Território Quilombola por Unidade da Federação",
        special=True,
    ),
    GeographyLevel("terra_indigena", 11, "Terra Indígena", special=True),
    GeographyLevel(
        "terra_indigena_uf", 12, "Terra Indígena por Unidade da Federação", special=True
    ),
    GeographyLevel("coordenacao_regional_funai", 13, "Coordenação Regional da Funai", special=True),
)
LEVELS_BY_ID = {level.id: level for level in LEVELS}

# Níveis que contêm inteiramente cada nível (todos os ancestrais, não só o pai).
ANCESTOR_LEVELS: dict[str, frozenset[str]] = {
    "brasil": frozenset(),
    "regiao": frozenset({"brasil"}),
    "uf": frozenset({"regiao", "brasil"}),
    "regiao_intermediaria": frozenset({"uf", "regiao", "brasil"}),
    "regiao_imediata": frozenset({"regiao_intermediaria", "uf", "regiao", "brasil"}),
    "municipio": frozenset({"regiao_imediata", "regiao_intermediaria", "uf", "regiao", "brasil"}),
    "amazonia_legal": frozenset({"brasil"}),
    "amazonia_legal_uf": frozenset({"amazonia_legal", "uf", "regiao", "brasil"}),
    "territorio_quilombola": frozenset({"brasil"}),
    "territorio_quilombola_uf": frozenset({"territorio_quilombola", "uf", "regiao", "brasil"}),
    "terra_indigena": frozenset({"brasil"}),
    "terra_indigena_uf": frozenset({"terra_indigena", "uf", "regiao", "brasil"}),
    "coordenacao_regional_funai": frozenset({"brasil"}),
}


def level_rank(level_id: str) -> int:
    """Ordem de apresentação do nível. Nível desconhecido gera ``ValueError``."""
    try:
        return LEVELS_BY_ID[level_id].rank
    except KeyError:
        msg = f"nível territorial desconhecido: {level_id!r} (válidos: {list(LEVELS_BY_ID)})"
        raise ValueError(msg) from None


def is_ancestor_level(ancestor: str, level: str) -> bool:
    """``ancestor`` contém inteiramente as unidades de ``level``."""
    level_rank(ancestor)
    level_rank(level)
    return ancestor in ANCESTOR_LEVELS[level]


def geography_key(level_id: str, code: str) -> str:
    """Chave determinística de território (``municipio:5101837``)."""
    level_rank(level_id)
    return f"{level_id}:{code}"
