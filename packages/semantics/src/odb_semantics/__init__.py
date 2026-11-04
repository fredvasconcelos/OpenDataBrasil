"""Camada semântica: catálogo de indicadores, hierarquias e regras de consulta."""

from odb_semantics.config import (
    Classification,
    FactConfig,
    IndicatorConfig,
    Partition,
    SemanticCatalog,
    SemanticConfigError,
    load_catalog,
    load_scope,
)
from odb_semantics.geography import (
    ANCESTOR_LEVELS,
    LEVELS,
    LEVELS_BY_ID,
    GeographyLevel,
    geography_key,
    is_ancestor_level,
    level_rank,
)
from odb_semantics.query import (
    IndicatorMeta,
    IndicatorQuery,
    QueryPlan,
    SemanticError,
    check_semantics,
    meta_from_rows,
    plan_query,
)

__all__ = [
    "ANCESTOR_LEVELS",
    "LEVELS",
    "LEVELS_BY_ID",
    "Classification",
    "FactConfig",
    "GeographyLevel",
    "IndicatorConfig",
    "IndicatorMeta",
    "IndicatorQuery",
    "Partition",
    "QueryPlan",
    "SemanticCatalog",
    "SemanticConfigError",
    "SemanticError",
    "check_semantics",
    "geography_key",
    "is_ancestor_level",
    "level_rank",
    "load_catalog",
    "load_scope",
    "meta_from_rows",
    "plan_query",
]
