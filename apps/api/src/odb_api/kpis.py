"""KPIs do portal: navegação, mapa, detalhe (tooltip), série e tabela.

Cada operação vira uma ``IndicatorQuery`` do planejador semântico. As regras
de nível, classificação e Total valem aqui como em qualquer consulta. As
dimensões pedidas precisam estar liberadas no KPI (``configs/portal``).

Combinações de categorias (``Combo``): uma tupla com uma categoria por
dimensão pedida, na ordem do portal. O Total da dimensão entra quando ela não
está detalhada. Exemplo, com cor ou raça e sexo:
``(c86:95251, c2:6794)`` é o Total, ``(c86:2779, c2:6794)`` é Parda e
``(c86:2779, c2:4)`` é Parda > Homens.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from odb_api.gold import GoldGateway, NotFoundError
from odb_api.portal import KpiConfig, PortalConfig, PortalConfigError, check_against_release
from odb_api.release import ReleaseContext
from odb_api.schemas import (
    CategoryOut,
    CellOut,
    ColumnOut,
    DetailNodeOut,
    DetailOut,
    DimensionOut,
    FilterOut,
    GeographyRefOut,
    KpiOut,
    KpiSourceOut,
    MapOut,
    MapValueOut,
    NavigationOut,
    PlannedKpiOut,
    PointOut,
    Provenance,
    SeriesItemOut,
    SeriesOut,
    SubthemeOut,
    TableOut,
    TableRowOut,
    TableVersionOut,
    ThemeOut,
)
from odb_semantics import (
    IndicatorQuery,
    Panorama,
    SemanticError,
    check_against_portal,
    plan_query,
    resolve_links,
)

Combo = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Observation:
    """Linha de resultado do planejador, já com a combinação de categorias."""

    geography_key: str
    name: str
    period: str
    combo: Combo
    value: Decimal | None
    status: str


def to_float(value: Decimal | None) -> float | None:
    """Decimal da Gold → número JSON (exato até 2^53 para contagens)."""
    return None if value is None else float(value)


def provenance(
    ctx: ReleaseContext, tables: Iterable[str], *, derived: bool = False, truncated: bool = False
) -> Provenance:
    """Tabelas e versões do release usadas na resposta."""
    return Provenance(
        release_id=ctx.release_id,
        tables=[
            TableVersionOut(table_id=t, delta_version=ctx.release.tables[t].delta_version)
            for t in sorted(set(tables))
            if t in ctx.release.tables
        ],
        derived=derived,
        truncated=truncated,
    )


class KpiService:
    """Operações do portal sobre os KPIs configurados."""

    def __init__(
        self,
        gold: GoldGateway,
        portal: PortalConfig,
        *,
        page_max: int,
        panorama: Panorama | None = None,
    ) -> None:
        """Recebe o acesso à Gold, a configuração do portal e, opcionalmente, o panorama.

        Com o panorama (ADR-0010), a navegação segue a sua taxonomia: os KPIs
        publicados entram no lugar indicado por ``kpi`` e os demais aparecem
        como planejados.
        """
        self._links: dict[str, str | None] = {}
        if panorama is not None:
            check_against_portal(panorama, {k.id: k for k in portal.kpis()})
            self._links = resolve_links(panorama, (k.id for k in portal.kpis()))
        self._gold = gold
        self._portal = portal
        self._panorama = panorama
        self._page_max = page_max
        self._checked: set[str] = set()

    # ------------------------------------------------------------- configuração

    def _check(self, ctx: ReleaseContext) -> None:
        if ctx.release_id not in self._checked:
            indicators = self._gold.indicators(ctx)
            check_against_release(self._portal, indicators, self._gold.partitions(ctx))
            if self._panorama is not None:
                self._check_panorama_tables(self._panorama, indicators)
            self._checked.add(ctx.release_id)

    def _check_panorama_tables(
        self, panorama: Panorama, indicators: Mapping[str, Mapping[str, Any]]
    ) -> None:
        """A tabela de origem publicada é a mesma que o panorama declara."""
        problems = []
        for _, _, item in panorama.items():
            link = self._links.get(item.id)
            kpi = self._portal.kpi(link) if link else None
            if kpi is None:  # planejado (a ligação com o portal já foi conferida)
                continue
            published = str(indicators[kpi.indicator]["source_table_id"])
            if published != item.tabela:
                problems.append(f"{item.id}: tabela {item.tabela} no panorama, {published} na Gold")
        if problems:
            raise PortalConfigError("; ".join(problems))

    def kpi(self, ctx: ReleaseContext, kpi_id: str) -> KpiConfig:
        """KPI configurado e conferido contra o release."""
        self._check(ctx)
        kpi = self._portal.kpi(kpi_id)
        if kpi is None:
            msg = f"KPI inexistente: {kpi_id}"
            raise NotFoundError(msg)
        return kpi

    def _dims(self, kpi: KpiConfig, requested: Sequence[str]) -> list[str]:
        exposed = [d.classification for d in kpi.dimensions]
        unknown = [d for d in requested if d not in exposed]
        if unknown:
            msg = f"{kpi.id}: dimensões não disponíveis {unknown} (disponíveis: {exposed})"
            raise SemanticError(msg)
        # Ordem fixa do portal, sem repetição.
        return [d for d in exposed if d in set(requested)]

    def _dimension_out(self, ctx: ReleaseContext, kpi: KpiConfig) -> list[DimensionOut]:
        out = []
        for dim in kpi.dimensions:
            cats = self._gold.partition_categories(ctx, dim.classification, dim.partition)
            out.append(
                DimensionOut(
                    classification_id=dim.classification,
                    label=dim.label,
                    partition_id=dim.partition,
                    total_category_key=self._gold.total_category(ctx, dim.classification)[
                        "category_key"
                    ],
                    categories=[
                        CategoryOut(
                            category_key=c["category_key"],
                            category_id=c["category_id"],
                            name=c["name"],
                        )
                        for c in cats
                    ],
                )
            )
        return out

    def describe(self, ctx: ReleaseContext, kpi: KpiConfig, theme: str, sub: str) -> KpiOut:
        """KPI com os metadados do indicador no release."""
        meta = self._gold.indicators(ctx)[kpi.indicator]
        geometry = set(self._gold.geometry_levels(ctx))
        levels = list(meta["available_levels"] or ())
        return KpiOut(
            kpi_id=kpi.id,
            label=kpi.label,
            theme_id=theme,
            subtheme_id=sub,
            indicator_id=kpi.indicator,
            name=meta["name"],
            description=meta["description"],
            unit=meta["unit"],
            additivity=meta["additivity"],
            periods=list(meta["periods"] or ()),
            levels=levels,
            map_levels=[lvl for lvl in levels if lvl in geometry],
            dimensions=self._dimension_out(ctx, kpi),
            caveats=list(meta["caveats"] or ()),
            source=KpiSourceOut(
                dataset_id=meta["dataset_id"],
                source_table_id=meta["source_table_id"],
                source_variable_id=meta["source_variable_id"],
                source_variable_name=meta.get("source_variable_name"),
                reference_url=meta.get("reference_url"),
                license_id=meta.get("license_id"),
            ),
        )

    def navigation(self, ctx: ReleaseContext) -> NavigationOut:
        """Temas, subtemas e KPIs (publicados e, com o panorama, planejados)."""
        self._check(ctx)
        themes = (
            self._panorama_themes(ctx, self._panorama)
            if self._panorama is not None
            else [
                ThemeOut(
                    theme_id=t.id,
                    label=t.label,
                    filters=[],
                    subthemes=[
                        SubthemeOut(
                            subtheme_id=s.id,
                            label=s.label,
                            kpis=[self.describe(ctx, k, t.id, s.id) for k in s.kpis],
                            planned=[],
                        )
                        for s in t.subthemes
                    ],
                )
                for t in self._portal.themes
            ]
        )
        return NavigationOut(
            release_id=ctx.release_id,
            scope=self._portal.scope,
            dimension_order=list(self._portal.dimension_order),
            themes=themes,
        )

    def _panorama_themes(self, ctx: ReleaseContext, panorama: Panorama) -> list[ThemeOut]:
        out = []
        for theme in panorama.temas:
            subthemes = []
            for sub in theme.subtemas:
                published = []
                for item in sub.kpis:
                    link = self._links.get(item.id)
                    kpi = self._portal.kpi(link) if link else None
                    if kpi is not None:
                        published.append(self.describe(ctx, kpi, theme.id, sub.id))
                planned = [
                    PlannedKpiOut(
                        kpi_id=item.id,
                        label=item.label,
                        source_table_id=item.tabela,
                        survey=item.pesquisa,
                        filters=list(item.filtros),
                        note=item.nota,
                    )
                    for item in sub.kpis
                    if self._links.get(item.id) is None
                ]
                subthemes.append(
                    SubthemeOut(
                        subtheme_id=sub.id, label=sub.label, kpis=published, planned=planned
                    )
                )
            out.append(
                ThemeOut(
                    theme_id=theme.id,
                    label=theme.label,
                    filters=[
                        FilterOut(filter_id=f, label=panorama.filter_label(f))
                        for f in theme.filtros
                    ],
                    subthemes=subthemes,
                )
            )
        return out

    # ------------------------------------------------------------- consulta

    def _period(self, ctx: ReleaseContext, kpi: KpiConfig, period: str | None) -> str:
        periods: list[str] = list(self._gold.indicators(ctx)[kpi.indicator]["periods"] or ())
        if period is None:
            if not periods:
                msg = f"{kpi.indicator} sem períodos publicados"
                raise NotFoundError(msg)
            return periods[-1]
        if period not in periods:
            msg = f"{kpi.indicator} não tem o período {period} (disponíveis: {periods})"
            raise SemanticError(msg)
        return period

    def _breakdown(
        self, ctx: ReleaseContext, kpi: KpiConfig, dims: Sequence[str]
    ) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        for dim in kpi.dimensions:
            if dim.classification in dims:
                total = self._gold.total_category(ctx, dim.classification)["category_id"]
                cats = self._gold.partition_categories(ctx, dim.classification, dim.partition)
                out[dim.classification] = (total, *(c["category_id"] for c in cats))
        return out

    def _observations(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        *,
        level: str,
        within: str | None,
        periods: Sequence[str],
        dims: Sequence[str],
        max_rows: int,
    ) -> tuple[list[Observation], Provenance]:
        query = IndicatorQuery(
            indicators=(kpi.indicator,),
            level=level,
            within=within,
            periods=tuple(periods),
            breakdown=self._breakdown(ctx, kpi, dims),
        )
        plan = plan_query(query, self._gold.indicator_meta(ctx))
        result = self._gold.run_plan(ctx, plan, max_rows=max_rows)
        out = []
        for r in result.rows:
            row = dict(zip(result.columns, r, strict=True))
            parts = {
                p.split(":", 1)[0]: p
                for p in str(row["breakdown_key"]).split("|")
                if p and p != "none"
            }
            out.append(
                Observation(
                    geography_key=row["geography_key"],
                    name=row["territory_name"],
                    period=row["period"],
                    combo=tuple(parts[d] for d in dims),
                    value=row["value"],
                    status=row["value_status"],
                )
            )
        return out, provenance(ctx, plan.aliases.values(), truncated=result.truncated)

    def _combos(self, ctx: ReleaseContext, kpi: KpiConfig, dims: Sequence[str]) -> list[Combo]:
        """Combinações em pré-ordem: Total, depois cada categoria e seus filhos."""
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        cats = {
            d.classification: [
                c["category_key"]
                for c in self._gold.partition_categories(ctx, d.classification, d.partition)
            ]
            for d in kpi.dimensions
            if d.classification in dims
        }
        out: list[Combo] = []

        def visit(prefix: list[str]) -> None:
            out.append(tuple(prefix + totals[len(prefix) :]))
            if len(prefix) < len(dims):
                for cat in cats[dims[len(prefix)]]:
                    visit([*prefix, cat])

        visit([])
        return out

    def _label(self, ctx: ReleaseContext, combo: Combo, dims: Sequence[str]) -> str:
        names = [
            self._gold.categories(ctx)[key]["name"]
            for key in combo
            if not self._gold.categories(ctx)[key]["is_total"]
        ]
        return " › ".join(names) if names else "Total"  # noqa: RUF001 - separador de exibição

    @staticmethod
    def _depth(ctx_combo: Combo, totals: Sequence[str]) -> int:
        return sum(1 for key, total in zip(ctx_combo, totals, strict=True) if key != total)

    def _ref(self, ctx: ReleaseContext, key: str) -> GeographyRefOut:
        geo = self._gold.geography(ctx, key)
        return GeographyRefOut(geography_key=key, name=geo["name"], level_id=geo["level_id"])

    def map(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        level: str,
        period: str | None,
        within: str | None,
    ) -> MapOut:
        """Total do KPI em cada território do nível."""
        kpi = self.kpi(ctx, kpi_id)
        chosen = self._period(ctx, kpi, period)
        obs, prov = self._observations(
            ctx, kpi, level=level, within=within, periods=(chosen,), dims=(), max_rows=50_000
        )
        meta = self._gold.indicators(ctx)[kpi.indicator]
        return MapOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            level=level,
            period=chosen,
            unit=meta["unit"],
            additivity=meta["additivity"],
            values=[
                MapValueOut(
                    geography_key=o.geography_key,
                    name=o.name,
                    value=to_float(o.value),
                    status=o.status,
                )
                for o in obs
            ],
            provenance=prov,
        )

    def detail(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        geography: str,
        period: str | None,
        dimensions: Sequence[str],
    ) -> DetailOut:
        """Sub-KPIs aninhados de um território (tooltip)."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        chosen = self._period(ctx, kpi, period)
        ref = self._ref(ctx, geography)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=ref.level_id,
            within=geography,
            periods=(chosen,),
            dims=dims,
            max_rows=10_000,
        )
        meta = self._gold.indicators(ctx)[kpi.indicator]
        additive = meta["additivity"] == "additive"
        values = {o.combo: o for o in obs if o.geography_key == geography}
        categories = self._gold.categories(ctx)
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]

        def node(combo: Combo, depth: int, parent: Observation | None) -> DetailNodeOut:
            found = values.get(combo)
            value = None if found is None else found.value
            share = None
            if additive and parent is not None and parent.value and value is not None:
                share = round(float(value / parent.value * 100), 2)
            children: list[DetailNodeOut] = []
            if depth < len(dims):
                dim = next(d for d in kpi.dimensions if d.classification == dims[depth])
                for cat in self._gold.partition_categories(ctx, dim.classification, dim.partition):
                    child = list(combo)
                    child[depth] = cat["category_key"]
                    children.append(node(tuple(child), depth + 1, found))
            key = combo[depth - 1] if depth else None
            return DetailNodeOut(
                label=categories[key]["name"] if key else "Total",
                classification_id=dims[depth - 1] if depth else None,
                category_key=key,
                value=to_float(value),
                status="absent" if found is None else found.status,
                share_pct=share,
                children=children,
            )

        return DetailOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            geography=ref,
            period=chosen,
            unit=meta["unit"],
            additivity=meta["additivity"],
            dimensions=dims,
            root=node(tuple(totals), 0, None),
            notes=list(meta["caveats"] or ()),
            provenance=prov,
        )

    def series(
        self, ctx: ReleaseContext, kpi_id: str, *, geography: str, dimensions: Sequence[str]
    ) -> SeriesOut:
        """Todos os períodos de um território, por combinação de categorias."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        ref = self._ref(ctx, geography)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=ref.level_id,
            within=geography,
            periods=(),
            dims=dims,
            max_rows=50_000,
        )
        by_combo: dict[Combo, list[Observation]] = {}
        for o in obs:
            if o.geography_key == geography:
                by_combo.setdefault(o.combo, []).append(o)
        series = [
            SeriesItemOut(
                key="|".join(combo) or "total",
                label=self._label(ctx, combo, dims),
                categories=dict(zip(dims, combo, strict=True)),
                points=[
                    PointOut(period=o.period, value=to_float(o.value), status=o.status)
                    for o in sorted(by_combo[combo], key=lambda x: x.period)
                ],
            )
            for combo in self._combos(ctx, kpi, dims)
            if combo in by_combo
        ]
        meta = self._gold.indicators(ctx)[kpi.indicator]
        return SeriesOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            geography=ref,
            unit=meta["unit"],
            series=series,
            provenance=prov,
        )

    def table(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        level: str,
        period: str | None,
        within: str | None,
        dimensions: Sequence[str],
        sort: str,
        descending: bool,
        offset: int,
        limit: int,
        locate: str | None = None,
    ) -> TableOut:
        """Territórios do nível, com o Total e as combinações de categorias.

        ``locate``: a página devolvida é a que contém esse território, na mesma
        ordenação (o portal localiza na tabela o território clicado no mapa). Se
        ele não estiver na tabela, vale ``offset``.
        """
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        chosen = self._period(ctx, kpi, period)
        limit = min(limit, self._page_max)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=(chosen,),
            dims=dims,
            max_rows=200_000,
        )
        combos = self._combos(ctx, kpi, dims)
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        keys = {c: "|".join(c) or "total" for c in combos}
        grid: dict[str, dict[str, Any]] = {}
        for o in obs:
            row = grid.setdefault(o.geography_key, {"name": o.name, "cells": {}})
            if o.combo in keys:
                row["cells"][keys[o.combo]] = CellOut(value=to_float(o.value), status=o.status)
        total_key = keys[combos[0]]

        def sort_key(item: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
            if sort == "name":
                return (item[1]["name"],)
            cell = item[1]["cells"].get(total_key)
            value = None if cell is None else cell.value
            # Ausentes sempre no fim, em qualquer direção.
            missing = value is None
            return (missing if descending else not missing, value or 0.0)

        ordered = sorted(grid.items(), key=sort_key, reverse=descending)
        if locate is not None:
            position = next((i for i, (key, _) in enumerate(ordered) if key == locate), None)
            if position is not None:
                offset = position // limit * limit
        page = ordered[offset : offset + limit]
        ufs = {
            g["geography_key"]: g["uf_abbreviation"]
            for g in self._gold.search_geographies(
                ctx, text=None, levels=(level,), within=within, limit=50_000
            )
        }
        meta = self._gold.indicators(ctx)[kpi.indicator]
        return TableOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            level=level,
            period=chosen,
            unit=meta["unit"],
            columns=[
                ColumnOut(
                    key=keys[c], label=self._label(ctx, c, dims), depth=self._depth(c, totals)
                )
                for c in combos
            ],
            rows=[
                TableRowOut(
                    geography_key=key,
                    name=data["name"],
                    uf_abbreviation=ufs.get(key),
                    cells=data["cells"],
                )
                for key, data in page
            ],
            total_rows=len(ordered),
            offset=offset,
            limit=limit,
            provenance=prov,
        )

    def export_rows(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        level: str,
        periods: Sequence[str],
        within: str | None,
        dimensions: Sequence[str],
        max_rows: int,
    ) -> tuple[KpiConfig, list[str], list[Observation], Provenance]:
        """Observações para exportação (formato longo)."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        for p in periods:
            self._period(ctx, kpi, p)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=periods,
            dims=dims,
            max_rows=max_rows + 1,
        )
        return kpi, dims, obs, prov
