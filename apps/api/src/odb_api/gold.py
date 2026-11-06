"""Leitura da Gold publicada pela API (DuckDB sobre tabelas Delta fixadas).

Todas as consultas são templates fixos deste módulo ou do planejador
semântico (``odb_semantics.plan_query``), com valores em ``$parâmetros``. As
tabelas entram como ``{{alias}}`` e são resolvidas pelo release da requisição.

Cache (§10.8): metadados pequenos (indicadores, categorias) e as coleções de
geometria são guardados em memória com o ``release_id`` na chave. Um release
novo invalida tudo, porque as chaves mudam. O cache é descartável e nunca
substitui a Gold.
"""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

from odb_api.release import ReleaseContext
from odb_query_engine import QueryResult, ReadEngine, ReadQuery
from odb_semantics import IndicatorMeta, QueryPlan, meta_from_rows

DIM_INDICATOR = "dim_indicator"
DIM_INDICATOR_NODE = "dim_indicator_node"
DIM_CATEGORY = "dim_category"
DIM_GEOGRAPHY = "dim_geography"
DIM_GEOMETRY = "dim_geometry"
BRIDGE = "bridge_geography_ancestor"

T = TypeVar("T")


class NotFoundError(LookupError):
    """Recurso inexistente no release."""


class _Lru:
    """Cache LRU pequeno e thread-safe."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._data: OrderedDict[tuple[str, ...], Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: tuple[str, ...], build: Callable[[], T]) -> T:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]  # type: ignore[no-any-return]
        value = build()
        with self._lock:
            self._data[key] = value
            while len(self._data) > self._size:
                self._data.popitem(last=False)
        return value


def rows(result: QueryResult) -> list[dict[str, Any]]:
    """Linhas como dicionários."""
    return [dict(zip(result.columns, r, strict=True)) for r in result.rows]


class GoldGateway:
    """Consultas à Gold do release resolvido."""

    def __init__(self, engine: ReadEngine, *, geometry_cache_size: int = 8) -> None:
        """Recebe o motor de leitura (restrito à raiz Gold)."""
        self._engine = engine
        self._meta = _Lru(16)
        self._geometry = _Lru(geometry_cache_size)

    # ------------------------------------------------------------- execução

    def execute(
        self,
        ctx: ReleaseContext,
        sql: str,
        tables: Mapping[str, str],
        params: Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = None,
    ) -> QueryResult:
        """Executa um template com tabelas do release."""
        return self._engine.execute(
            ReadQuery(
                sql,
                {alias: ctx.pinned(table) for alias, table in tables.items()},
                params=dict(params or {}),
                max_rows=max_rows,
            )
        )

    def run_plan(self, ctx: ReleaseContext, plan: QueryPlan, *, max_rows: int) -> QueryResult:
        """Executa um plano do planejador semântico."""
        return self.execute(ctx, plan.sql_template, plan.aliases, plan.params, max_rows=max_rows)

    # ------------------------------------------------------------- metadados

    def indicators(self, ctx: ReleaseContext) -> dict[str, dict[str, Any]]:
        """``dim_indicator`` do release, por identificador."""

        def build() -> dict[str, dict[str, Any]]:
            result = self.execute(
                ctx, "SELECT * FROM {{ind}} ORDER BY node_key", {"ind": DIM_INDICATOR}
            )
            return {r["indicator_id"]: r for r in rows(result)}

        return self._meta.get((ctx.release_id, "indicators"), build)

    def indicator_meta(self, ctx: ReleaseContext) -> dict[str, IndicatorMeta]:
        """Metadados para o planejador semântico."""
        return self._meta.get(
            (ctx.release_id, "indicator_meta"),
            lambda: meta_from_rows(list(self.indicators(ctx).values())),
        )

    def categories(self, ctx: ReleaseContext) -> dict[str, dict[str, Any]]:
        """``dim_category`` do release, por chave de categoria."""

        def build() -> dict[str, dict[str, Any]]:
            result = self.execute(
                ctx,
                "SELECT * FROM {{cat}} ORDER BY classification_id, sort_order",
                {"cat": DIM_CATEGORY},
                max_rows=100_000,
            )
            return {r["category_key"]: r for r in rows(result)}

        return self._meta.get((ctx.release_id, "categories"), build)

    def partitions(self, ctx: ReleaseContext) -> dict[str, list[str]]:
        """Partições publicadas por classificação."""
        out: dict[str, list[str]] = {}
        for cat in self.categories(ctx).values():
            pid = cat.get("partition_id")
            if pid and pid not in out.setdefault(cat["classification_id"], []):
                out[cat["classification_id"]].append(pid)
        return out

    def partition_categories(
        self, ctx: ReleaseContext, classification_id: str, partition_id: str
    ) -> list[dict[str, Any]]:
        """Categorias de uma partição, na ordem oficial."""
        return [
            c
            for c in self.categories(ctx).values()
            if c["classification_id"] == classification_id and c["partition_id"] == partition_id
        ]

    def total_category(self, ctx: ReleaseContext, classification_id: str) -> dict[str, Any]:
        """Categoria Total de uma classificação."""
        for c in self.categories(ctx).values():
            if c["classification_id"] == classification_id and c["is_total"]:
                return c
        msg = f"classificação sem Total no release: {classification_id}"
        raise NotFoundError(msg)

    def tree(self, ctx: ReleaseContext) -> list[dict[str, Any]]:
        """Árvore temática da Gold (``dim_indicator_node``)."""
        result = self.execute(
            ctx,
            "SELECT node_key, parent_key, node_type, label, depth, indicator_id, "
            "classification_id, category_key FROM {{nodes}} ORDER BY sort_order",
            {"nodes": DIM_INDICATOR_NODE},
            max_rows=50_000,
        )
        return rows(result)

    # ------------------------------------------------------------- territórios

    def geography(self, ctx: ReleaseContext, key: str) -> dict[str, Any]:
        """Um território da ``dim_geography``."""
        result = self.execute(
            ctx,
            "SELECT * FROM {{geo}} WHERE geography_key = $key",
            {"geo": DIM_GEOGRAPHY},
            {"key": key},
            max_rows=1,
        )
        found = rows(result)
        if not found:
            msg = f"território inexistente no release: {key}"
            raise NotFoundError(msg)
        return found[0]

    def search_geographies(
        self,
        ctx: ReleaseContext,
        *,
        text: str | None,
        levels: Sequence[str],
        within: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Busca por nome (sem acentos e sem caixa), nível e recorte."""
        where = ["1 = 1"]
        params: dict[str, Any] = {}
        tables = {"geo": DIM_GEOGRAPHY}
        if text:
            where.append("strip_accents(lower(g.name)) LIKE '%' || strip_accents(lower($q)) || '%'")
            params["q"] = text
        if levels:
            where.append("list_contains(CAST($levels AS VARCHAR[]), g.level_id)")
            params["levels"] = list(levels)
        if within:
            where.append(
                "EXISTS (SELECT 1 FROM {{anc}} AS a WHERE a.geography_key = g.geography_key "
                "AND a.ancestor_key = $within)"
            )
            params["within"] = within
            tables["anc"] = BRIDGE
        sql = (
            "SELECT g.geography_key, g.level_id, g.level_name, g.territory_code, g.name, "
            "g.uf_abbreviation, g.parent_key FROM {{geo}} AS g WHERE "
            + " AND ".join(where)
            + " ORDER BY g.level_rank, length(g.name), g.name"
        )
        return rows(self.execute(ctx, sql, tables, params, max_rows=limit))

    def ancestors(self, ctx: ReleaseContext, key: str) -> list[dict[str, Any]]:
        """Ancestrais de um território (do mais próximo ao Brasil)."""
        result = self.execute(
            ctx,
            "SELECT a.ancestor_key, a.ancestor_level, a.distance, g.name FROM {{anc}} AS a "
            "JOIN {{geo}} AS g ON g.geography_key = a.ancestor_key "
            "WHERE a.geography_key = $key AND a.distance > 0 ORDER BY a.distance",
            {"anc": BRIDGE, "geo": DIM_GEOGRAPHY},
            {"key": key},
            max_rows=100,
        )
        return rows(result)

    def geometry_levels(self, ctx: ReleaseContext) -> list[str]:
        """Níveis com geometria no release."""
        if not ctx.has(DIM_GEOMETRY):
            return []

        def build() -> list[str]:
            result = self.execute(
                ctx,
                "SELECT DISTINCT level_id FROM {{gm}} ORDER BY level_id",
                {"gm": DIM_GEOMETRY},
            )
            return [r[0] for r in result.rows]

        return self._meta.get((ctx.release_id, "geometry_levels"), build)

    def geometry_collection(self, ctx: ReleaseContext, level: str, within: str | None) -> bytes:
        """``FeatureCollection`` GeoJSON do nível (opcionalmente dentro de um recorte)."""
        if level not in self.geometry_levels(ctx):
            msg = f"nível sem geometria no release: {level}"
            raise NotFoundError(msg)

        def build() -> bytes:
            tables = {"gm": DIM_GEOMETRY, "geo": DIM_GEOGRAPHY}
            where = "m.level_id = $level"
            params: dict[str, Any] = {"level": level}
            if within:
                where += (
                    " AND EXISTS (SELECT 1 FROM {{anc}} AS a WHERE a.geography_key = "
                    "m.geography_key AND a.ancestor_key = $within)"
                )
                params["within"] = within
                tables["anc"] = BRIDGE
            result = self.execute(
                ctx,
                "SELECT m.geography_key, g.name, g.uf_abbreviation, m.geometry_geojson, "
                "m.derivation, m.reference_year FROM {{gm}} AS m "
                "JOIN {{geo}} AS g ON g.geography_key = m.geography_key "
                f"WHERE {where} ORDER BY m.geography_key",
                tables,
                params,
                max_rows=20_000,
            )
            # A geometria já está em GeoJSON na Gold: é inserida sem reserializar.
            features = ",".join(
                '{"type":"Feature","id":'
                + json.dumps(r["geography_key"])
                + ',"properties":'
                + json.dumps({"name": r["name"], "uf": r["uf_abbreviation"]}, ensure_ascii=False)
                + ',"geometry":'
                + r["geometry_geojson"]
                + "}"
                for r in rows(result)
            )
            meta = json.dumps({"release_id": ctx.release_id, "level": level, "within": within})
            return (
                '{"type":"FeatureCollection","metadata":' + meta + ',"features":[' + features + "]}"
            ).encode()

        return self._geometry.get((ctx.release_id, "geometry", level, within or ""), build)
