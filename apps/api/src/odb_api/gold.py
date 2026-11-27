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

import gzip
import json
import re
import threading
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

from odb_api import telemetry
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


# Numeração de tópicos no início do nome ("2.1.2 ", "12.", "1 ") seguida de texto.
_OUTLINE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s*(?=[^\d\s.,%])")


def clean_label(name: str) -> str:
    """Nome de categoria sem a numeração de tópicos da fonte (DS 2.3.6).

    "2.1.2 Habitação" → "Habitação"; "1.Cereais e leguminosas" → "Cereais e
    leguminosas". Nomes que começam por número de verdade ("0 a 4 anos",
    "1 morador", "2022") ficam como estão.
    """
    cleaned = _OUTLINE.sub("", name, count=1)
    return cleaned if cleaned and cleaned != name and not _KEEP.match(name) else name


# Começos numéricos que fazem parte do nome (faixas, contagens, anos).
_KEEP = re.compile(
    r"^\s*\d+(?:[.,]\d+)?\s*(?:a|até|ou|e|anos?|m[eê]s|meses|semanas?|dias?|horas?|morador|moradores|"
    r"pessoas?|salários?|SM|%|kg|km|vezes|filhos?|cômodos?|banheiros?|dormitórios?)\b",
    re.IGNORECASE,
)


class GoldGateway:
    """Consultas à Gold do release resolvido."""

    def __init__(self, engine: ReadEngine, *, geometry_cache_size: int = 8) -> None:
        """Recebe o motor de leitura (restrito à raiz Gold)."""
        self._engine = engine
        self._meta = _Lru(16)
        self._geometry = _Lru(geometry_cache_size)
        self._geometry_build_lock = threading.Lock()
        self._coverage_meta = _Lru(64)

    # ------------------------------------------------------------- execução

    def execute(
        self,
        ctx: ReleaseContext,
        sql: str,
        tables: Mapping[str, str],
        params: Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = None,
        for_export: bool = False,
    ) -> QueryResult:
        """Executa um template com tabelas do release (com span e métrica OpenTelemetry)."""
        with telemetry.duckdb_span(tables, ctx.release_id) as span:
            result = self._engine.execute(
                ReadQuery(
                    sql,
                    {alias: ctx.pinned(table) for alias, table in tables.items()},
                    params=dict(params or {}),
                    max_rows=max_rows,
                    purpose="export" if for_export else "query",
                )
            )
            span.set_attribute("odb.rows", len(result.rows))
            span.set_attribute("odb.truncated", result.truncated)
        telemetry.record_query(
            tables, result.elapsed_ms / 1000, len(result.rows), truncated=result.truncated
        )
        return result

    def run_plan(
        self, ctx: ReleaseContext, plan: QueryPlan, *, max_rows: int, for_export: bool = False
    ) -> QueryResult:
        """Executa um plano do planejador semântico."""
        return self.execute(
            ctx,
            plan.sql_template,
            plan.aliases,
            plan.params,
            max_rows=max_rows,
            for_export=for_export,
        )

    # ------------------------------------------------------------- metadados

    def count_plan(
        self, ctx: ReleaseContext, plan: QueryPlan, *, total_categories: Sequence[str] = ()
    ) -> int:
        """Conta a saída real do plano sem transportar valores ao Python (Plano D, D4).

        Dimensões filtradas fora do pivot voltam ao Total após a leitura; aplicamos
        exatamente a mesma seleção aqui. Lacunas não são preenchidas nem estimadas.
        """
        params = dict(plan.params)
        conditions = []
        for i, category in enumerate(total_categories):
            key = f"pivot_total_{i}"
            conditions.append(f"strpos('|' || breakdown_key || '|', ${key}) > 0")
            params[key] = f"|{category}|"
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        result = self.execute(
            ctx,
            f"SELECT count(*) FROM ({plan.sql_template}) AS pivot_count{where}",
            plan.aliases,
            params,
            max_rows=1,
        )
        return int(result.rows[0][0])

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

    def periods_by_level(self, ctx: ReleaseContext) -> dict[str, dict[str, list[str]]]:
        """Períodos efetivamente publicados por indicador e nível territorial.

        Séries Censo + PNAD e edições da POF têm coberturas diferentes. O índice
        pequeno fica no cache do release; os valores continuam só na Gold Delta.
        """

        def build() -> dict[str, dict[str, list[str]]]:
            result = self.execute(
                ctx,
                "SELECT indicator_id, level_id, array_agg(DISTINCT period ORDER BY period) "
                "AS periods FROM {{obs}} GROUP BY indicator_id, level_id",
                {"obs": "indicator_observation"},
                max_rows=100_000,
            )
            if result.truncated:
                msg = "Índice de períodos por nível excedeu o limite de metadados do release"
                raise RuntimeError(msg)
            out: dict[str, dict[str, list[str]]] = {}
            for row in rows(result):
                out.setdefault(row["indicator_id"], {})[row["level_id"]] = row["periods"]
            return out

        return self._meta.get((ctx.release_id, "periods_by_level"), build)

    def categories(self, ctx: ReleaseContext) -> dict[str, dict[str, Any]]:
        """``dim_category`` do release, por chave de categoria."""

        def build() -> dict[str, dict[str, Any]]:
            result = self.execute(
                ctx,
                "SELECT * FROM {{cat}} ORDER BY classification_id, sort_order",
                {"cat": DIM_CATEGORY},
                max_rows=100_000,
            )
            # Rótulo limpo para leitura (DS 2.3.6): sem a numeração da fonte ("2.1.2
            # Habitação" → "Habitação"); a hierarquia aparece pelo recuo. O nome oficial
            # fica em ``official_name``.
            return {
                r["category_key"]: {
                    **r,
                    "official_name": r["name"],
                    "name": clean_label(str(r["name"])),
                }
                for r in rows(result)
            }

        return self._meta.get((ctx.release_id, "categories"), build)

    def coverage(self, ctx: ReleaseContext) -> dict[str, dict[str, dict[str, Any]]]:
        """O que cada tabela de origem traz a cada indicador, como está no release.

        Indicador → tabela de origem (``source_table_id``) → ``levels`` e ``periods``
        publicados e ``classifications``: classificação com categorias além do Total →
        níveis em que aparecem. Mostra as tabelas-irmãs de um KPI (cada detalhe vem de
        uma tabela SIDRA) e os níveis em que um detalhe existe de fato (DS 2.9).
        Uma consulta por release, guardada no cache de metadados.
        """

        def build() -> dict[str, dict[str, dict[str, Any]]]:
            result = self.execute(
                ctx,
                "WITH k AS (SELECT DISTINCT indicator_id, source_table_id, level_id, period, "
                "breakdown_key FROM {{obs}}), "
                "p AS (SELECT indicator_id, source_table_id, level_id, period, "
                "unnest(string_split(breakdown_key, '|')) AS part FROM k) "
                "SELECT p.indicator_id, p.source_table_id, c.classification_id, p.level_id, "
                "list(DISTINCT p.level_id ORDER BY p.level_id) AS levels, "
                "list(DISTINCT p.period ORDER BY p.period) AS periods "
                "FROM p LEFT JOIN {{cat}} AS c ON c.category_key = p.part AND NOT c.is_total "
                "GROUP BY ALL",
                {"obs": "indicator_observation", "cat": DIM_CATEGORY},
                max_rows=200_000,
            )
            if result.truncated:
                msg = "Índice de tabelas de origem excedeu o limite de metadados do release"
                raise RuntimeError(msg)
            out: dict[str, dict[str, dict[str, Any]]] = {}
            for row in rows(result):
                table = out.setdefault(row["indicator_id"], {}).setdefault(
                    str(row["source_table_id"]),
                    {
                        "levels": set(),
                        "periods": set(),
                        "classifications": {},
                        "detail_periods": {},
                    },
                )
                table["levels"].update(row["levels"])
                table["periods"].update(row["periods"])
                if row["classification_id"] is not None:
                    table["classifications"].setdefault(row["classification_id"], set()).update(
                        row["levels"]
                    )
                    table["detail_periods"].setdefault(row["classification_id"], {}).setdefault(
                        row["level_id"], set()
                    ).update(row["periods"])
            return out

        return self._meta.get((ctx.release_id, "coverage"), build)

    def reference_counts(
        self, ctx: ReleaseContext, level: str, within: str | None
    ) -> list[dict[str, Any]]:
        """Conta só territórios da referência fixada; o chamador verifica o ano.

        A dimensão atual não tem validade histórica por unidade. Esta contagem não
        pode ser usada para outro ano nem para os recortes especiais do SIDRA.
        """

        def build() -> list[dict[str, Any]]:
            result = self.execute(
                ctx,
                "SELECT g.reference, count(*) AS territories FROM {{geo}} g "
                "WHERE g.in_reference AND g.level_id = $level AND "
                "($within IS NULL OR g.geography_key = $within OR g.geography_key IN "
                "(SELECT geography_key FROM {{anc}} WHERE ancestor_key = $within)) "
                "GROUP BY g.reference ORDER BY g.reference",
                {"geo": DIM_GEOGRAPHY, "anc": BRIDGE},
                {"level": level, "within": within},
            )
            if result.truncated:
                raise RuntimeError("Referência territorial truncada; rever o limite de metadados")
            return rows(result)

        return self._coverage_meta.get((ctx.release_id, "reference", level, within or ""), build)

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

    def observed_category_keys(
        self, ctx: ReleaseContext, indicator_id: str, classification_id: str
    ) -> set[str]:
        """Categorias presentes no indicador; não certifica completude por recorte."""

        def build() -> set[str]:
            result = self.execute(
                ctx,
                "SELECT DISTINCT part AS category_key FROM "
                "(SELECT unnest(string_split(breakdown_key, '|')) AS part "
                "FROM {{obs}} WHERE indicator_id = $indicator) "
                "WHERE split_part(part, ':', 1) = $classification",
                {"obs": "indicator_observation"},
                {"indicator": indicator_id, "classification": classification_id},
                max_rows=10_000,
            )
            if result.truncated:
                raise RuntimeError("categorias observadas excederam o limite de metadados")
            return {str(row["category_key"]) for row in rows(result)}

        return self._meta.get((ctx.release_id, f"native:{indicator_id}:{classification_id}"), build)

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
            where.append("g.level_id = ANY(CAST($levels AS VARCHAR[]))")
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

    def geography_counts(self, ctx: ReleaseContext, within: str | None) -> dict[str, int]:
        """Conta os territórios reais por nível no recorte, uma vez por release (D6)."""
        if within:
            self.geography(ctx, within)

        def build() -> dict[str, int]:
            tables = {"geo": DIM_GEOGRAPHY}
            params: dict[str, Any] = {}
            where = ""
            if within:
                where = (
                    " WHERE EXISTS (SELECT 1 FROM {{anc}} AS a "
                    "WHERE a.geography_key = g.geography_key AND a.ancestor_key = $within)"
                )
                tables["anc"] = BRIDGE
                params["within"] = within
            result = self.execute(
                ctx,
                "SELECT g.level_id, count(*) FROM {{geo}} AS g" + where + " GROUP BY g.level_id",
                tables,
                params,
            )
            return {str(row[0]): int(row[1]) for row in result.rows}

        return self._meta.get((ctx.release_id, "geography_counts", within or ""), build)

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
        return self.geometry_payload(ctx, level, within, compressed=False)

    def geometry_payload(
        self, ctx: ReleaseContext, level: str, within: str | None, *, compressed: bool
    ) -> bytes:
        """GeoJSON e gzip reutilizáveis por release, nível e recorte (Plano D, D3)."""
        if level not in self.geometry_levels(ctx):
            msg = f"nível sem geometria no release: {level}"
            raise NotFoundError(msg)

        def build() -> tuple[bytes, bytes]:
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
            body = (
                '{"type":"FeatureCollection","metadata":' + meta + ',"features":[' + features + "]}"
            ).encode()
            return body, gzip.compress(body, compresslevel=6, mtime=0)

        # Uma malha municipal custa CPU: pedidos simultâneos também reutilizam a primeira
        # montagem e compressão, sem guardar cópia oficial fora da Gold (§10.8).
        with self._geometry_build_lock:
            payload = self._geometry.get((ctx.release_id, "geometry", level, within or ""), build)
        return payload[1 if compressed else 0]
