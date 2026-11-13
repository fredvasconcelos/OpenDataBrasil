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

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from odb_api.gold import GoldGateway, NotFoundError
from odb_api.release import ReleaseContext
from odb_api.schemas import (
    CategoryOut,
    CellOut,
    ColumnOut,
    CorrectionOut,
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
    TimeGrainOut,
)
from odb_semantics import (
    IndicatorQuery,
    Panorama,
    SemanticError,
    check_against_portal,
    plan_query,
    resolve_links,
)
from odb_semantics.periods import (
    GRAIN_LABELS,
    MONTH_SHORT,
    PeriodError,
    complete_periods_at,
    months_of,
    parse_period,
    periods_at,
)
from odb_semantics.portal import (
    CorrectionConfig,
    KpiConfig,
    PortalConfig,
    PortalConfigError,
    describe_problems,
    release_problems,
)

logger = logging.getLogger(__name__)

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
        provenance: Mapping[str, tuple[str, str | None]] | None = None,
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
        # dataset → (sigla da instituição, sistema), das fontes configuradas.
        self._provenance = dict(provenance or {})
        # (release, indicador do índice) → grupo → mês → índice encadeado (ADR-0020).
        self._indexes: dict[tuple[str, str], dict[str, dict[str, Decimal]]] = {}
        # release → KPIs com problema contra ele (ADR-0015).
        self._unavailable: dict[str, dict[str, list[str]]] = {}

    # ------------------------------------------------------------- configuração

    def unavailable(self, ctx: ReleaseContext) -> dict[str, list[str]]:
        """KPIs da configuração incoerentes com o release, com os problemas.

        Conferência tolerante (ADR-0015): um KPI com problema (indicador fora do
        release, classificação ou partição ausente, tabela diferente da do
        panorama) sai da navegação e responde 404, e os demais seguem no ar. A
        conferência rígida roda no worker, antes de ativar o release
        (``odb release check``). Feita uma vez por release.
        """
        found = self._unavailable.get(ctx.release_id)
        if found is None:
            found = release_problems(
                self._portal,
                self._gold.indicators(ctx),
                self._gold.partitions(ctx),
                self._panorama,
            )
            if found:
                logger.warning(
                    "portal.kpis_indisponiveis",
                    extra={
                        "release_id": ctx.release_id,
                        "kpis": sorted(found),
                        "problems": describe_problems(found),
                    },
                )
            self._unavailable[ctx.release_id] = found
        return found

    def _available(self, ctx: ReleaseContext, kpi: KpiConfig | None) -> KpiConfig | None:
        """O KPI, se existir e estiver coerente com o release."""
        if kpi is None or kpi.id in self.unavailable(ctx):
            return None
        return kpi

    def kpi(self, ctx: ReleaseContext, kpi_id: str) -> KpiConfig:
        """KPI configurado e coerente com o release."""
        kpi = self._portal.kpi(kpi_id)
        if kpi is None:
            msg = f"KPI inexistente: {kpi_id}"
            raise NotFoundError(msg)
        if kpi_id in self.unavailable(ctx):
            msg = f"KPI indisponível no release {ctx.release_id}: {kpi_id}"
            raise NotFoundError(msg)
        return kpi

    def _dims(self, kpi: KpiConfig, requested: Sequence[str]) -> list[str]:
        exposed = [d.classification for d in kpi.dimensions]
        unknown = [d for d in requested if d not in exposed]
        if unknown:
            msg = f"{kpi.id}: dimensões não disponíveis {unknown} (disponíveis: {exposed})"
            raise SemanticError(msg)
        chosen = [d for d in exposed if d in set(requested)]  # ordem do portal, sem repetição
        if kpi.exclusive_dimensions and len(chosen) > 1:
            msg = (
                f"{kpi.id}: detalhe uma dimensão por vez (cada uma vem com as demais no Total,"
                " sem os cruzamentos)"
            )
            raise SemanticError(msg)
        return chosen

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
            map_levels=[
                lvl
                for lvl in levels
                if lvl in geometry and (kpi.map_levels is None or lvl in kpi.map_levels)
            ],
            dimensions=self._dimension_out(ctx, kpi),
            exclusive_dimensions=kpi.exclusive_dimensions,
            corrections=[
                CorrectionOut(correction_id=c.id, label=c.label, note=c.note)
                for c in kpi.corrections
            ],
            caveats=list(meta["caveats"] or ()),
            time_grains=self._time_grains(kpi, meta),
            time_aggregation=(
                meta.get("time_aggregation") if len(meta.get("time_grains") or ()) > 1 else None
            ),
            source=KpiSourceOut(
                dataset_id=meta["dataset_id"],
                source_table_id=meta["source_table_id"],
                source_variable_id=meta["source_variable_id"],
                source_variable_name=meta.get("source_variable_name"),
                reference_url=meta.get("reference_url"),
                license_id=meta.get("license_id"),
                institution=self._provenance.get(meta["dataset_id"], (None, None))[0],
                system=self._provenance.get(meta["dataset_id"], (None, None))[1],
            ),
        )

    @staticmethod
    def _time_grains(kpi: KpiConfig, meta: Mapping[str, Any]) -> list[TimeGrainOut]:
        """Grãos de tempo do KPI com os períodos de cada um (ADR-0013)."""
        base = list(meta["periods"] or ())
        grains = list(meta.get("time_grains") or ())
        if kpi.map_share is not None:
            grains = grains[:1]
        return [
            TimeGrainOut(
                grain=g,
                label=GRAIN_LABELS[g],
                periods=periods_at(base, g) if i else base,
                complete_periods=complete_periods_at(base, g) if i else base,
            )
            for i, g in enumerate(grains)
        ]

    def navigation(self, ctx: ReleaseContext) -> NavigationOut:
        """Temas, subtemas e KPIs (publicados e, com o panorama, planejados).

        KPIs incoerentes com o release ficam de fora (``unavailable``).
        """
        if self._panorama is not None:
            themes = self._panorama_themes(ctx, self._panorama)
        else:
            themes = []
            for t in self._portal.themes:
                subthemes = [
                    SubthemeOut(
                        subtheme_id=s.id,
                        label=s.label,
                        kpis=[
                            self.describe(ctx, k, t.id, s.id)
                            for k in s.kpis
                            if self._available(ctx, k)
                        ],
                        planned=[],
                    )
                    for s in t.subthemes
                ]
                subthemes = [s for s in subthemes if s.kpis]
                if subthemes:
                    themes.append(
                        ThemeOut(theme_id=t.id, label=t.label, filters=[], subthemes=subthemes)
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
                    kpi = self._available(ctx, self._portal.kpi(link) if link else None)
                    if kpi is not None:
                        published.append(self.describe(ctx, kpi, theme.id, sub.id))
                # KPIs curados de outras fontes (itens `externos`, ex.: Sinesp), após os do SIDRA.
                for external in sub.externos:
                    kpi = self._available(ctx, self._portal.kpi(external.kpi))
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

    def _grain(self, ctx: ReleaseContext, kpi: KpiConfig, grain: str | None) -> str | None:
        """Grão de tempo pedido, validado; ``None`` quando é o grão publicado (ADR-0013)."""
        if grain is None:
            return None
        grains = list(self._gold.indicators(ctx)[kpi.indicator].get("time_grains") or ())
        if grain not in grains:
            msg = f"{kpi.indicator} não pode ser detalhado por {grain} (disponível: {grains})"
            raise SemanticError(msg)
        if grain == grains[0]:
            return None
        if kpi.map_share is not None:
            msg = f"{kpi.id}: o mapa em % de uma categoria não é agregado no tempo"
            raise SemanticError(msg)
        return grain

    def _period(
        self, ctx: ReleaseContext, kpi: KpiConfig, period: str | None, grain: str | None = None
    ) -> str:
        """Período pedido, validado no grão; sem período, o último completo do grão."""
        base: list[str] = list(self._gold.indicators(ctx)[kpi.indicator]["periods"] or ())
        periods = periods_at(base, grain) if grain else base
        if period is None:
            if not periods:
                msg = f"{kpi.indicator} sem períodos publicados"
                raise NotFoundError(msg)
            complete = complete_periods_at(base, grain) if grain else periods
            return (complete or periods)[-1]
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
        grain: str | None = None,
        correction: str | None = None,
    ) -> tuple[list[Observation], Provenance]:
        query = IndicatorQuery(
            indicators=(kpi.indicator,),
            level=level,
            within=within,
            periods=tuple(periods),
            breakdown=self._breakdown(ctx, kpi, dims),
            grain=grain,
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
        prov = provenance(
            ctx, plan.aliases.values(), derived=plan.derived, truncated=result.truncated
        )
        if correction:
            out, prov = self._corrected(ctx, kpi, correction, out, dims=dims, prov=prov)
        return out, prov

    # ------------------------------------------------------------- correção de preços

    def _correction(self, kpi: KpiConfig, correction_id: str) -> CorrectionConfig:
        corr = next((c for c in kpi.corrections if c.id == correction_id), None)
        if corr is None:
            known = [c.id for c in kpi.corrections]
            msg = f"{kpi.id}: correção {correction_id!r} indisponível (disponíveis: {known})"
            raise SemanticError(msg)
        return corr

    def _price_index(
        self, ctx: ReleaseContext, corr: CorrectionConfig
    ) -> dict[str, dict[str, Decimal]]:
        """Grupo do índice → mês → número-índice encadeado (base: o primeiro mês = 1)."""
        key = (ctx.release_id, corr.indicator)
        if key not in self._indexes:
            query = IndicatorQuery(
                indicators=(corr.indicator,),
                level="brasil",
                breakdown={corr.group_classification: None},
            )
            plan = plan_query(query, self._gold.indicator_meta(ctx))
            result = self._gold.run_plan(ctx, plan, max_rows=100_000)
            by_group: dict[str, list[tuple[str, Decimal]]] = {}
            for r in result.rows:
                row = dict(zip(result.columns, r, strict=True))
                if row["value"] is None:
                    continue
                group = str(row["breakdown_key"]).split(":", 1)[-1]
                by_group.setdefault(group, []).append((row["period"], Decimal(row["value"])))
            indexes: dict[str, dict[str, Decimal]] = {}
            for group, points in by_group.items():
                level, chain = Decimal(1), {}
                for month, change in sorted(points):
                    level *= 1 + change / 100
                    chain[month] = level
                indexes[group] = chain
            self._indexes[key] = indexes
        return self._indexes[key]

    def _corrected(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        correction_id: str,
        obs: list[Observation],
        *,
        dims: Sequence[str],
        prov: Provenance,
    ) -> tuple[list[Observation], Provenance]:
        """Valores a preços do período mais recente coberto pelo índice (ADR-0020).

        fator = I(base) ÷ I(período), com I o índice encadeado das variações mensais do
        grupo (ou do índice geral). I de um período é o do mês de referência dele
        (``reference = "months"``) ou a média dos meses do próprio período
        (``reference = "period"``). Sem o fator (meses fora da série do índice), o valor
        fica sem valor.
        """
        corr = self._correction(kpi, correction_id)
        periods = list(self._gold.indicators(ctx)[kpi.indicator]["periods"] or ())
        indexes = self._price_index(ctx, corr)
        general = indexes.get(corr.general, {})

        base_period = correction_base(corr, general, periods)
        if base_period is None:
            msg = f"{kpi.id}: nenhum período coberto pelo índice de {corr.id}"
            raise SemanticError(msg)

        def level(chain: Mapping[str, Decimal], period: str) -> Decimal | None:
            return index_level(corr, chain, period)

        position = dims.index(corr.dimension) if corr.dimension in dims else None
        out = []
        categories = self._gold.categories(ctx)

        def group_of(key: str) -> str:
            # O grupo da categoria ou do ancestral mais próximo que tiver grupo.
            seen: set[str] = set()
            while key and key not in seen:
                seen.add(key)
                code = key.split(":", 1)[-1]
                if code in corr.groups:
                    return corr.groups[code]
                key = str((categories.get(key) or {}).get("parent_category_key") or "")
            return corr.general

        for o in obs:
            group = corr.general
            if position is not None and corr.groups:
                group = group_of(o.combo[position])
            chain = indexes.get(group, {})
            start, end = level(chain, o.period), level(chain, base_period)
            value = o.value
            status = o.status
            if value is not None:
                if start is None or end is None:
                    value, status = None, "not_available"
                else:
                    # A média no tempo (ADR-0017) chega como float do DuckDB.
                    value = Decimal(str(value)) * end / start
            out.append(Observation(o.geography_key, o.name, o.period, o.combo, value, status))
        base_ref = (
            reference_months(corr, base_period)[0] if corr.reference == "months" else base_period
        )
        base = _price_base(base_ref)
        prov = prov.model_copy(
            update={
                "derived": True,
                "correction": corr.id,
                "correction_label": corr.label,
                "price_base": base,
            }
        )
        return out, prov

    def _combos(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        dims: Sequence[str],
        *,
        row_totals: bool = False,
    ) -> list[Combo]:
        """Combinações em pré-ordem: Total, depois cada categoria e seus filhos.

        ``row_totals``: com duas ou mais dimensões, também o Total da primeira cruzado com
        as demais (Total e Homens), logo depois do Total: os totais de linha da matriz.
        """
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
        if row_totals and len(dims) > 1:
            extra: list[Combo] = []
            for cat in cats[dims[1]]:
                saved, out[:] = list(out), []
                visit([totals[0], cat])
                extra += out
                out[:] = saved
            out[1:1] = extra
        return out

    def _footer(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        *,
        level: str,
        within: str | None,
        period: str,
        dims: Sequence[str],
        keys: Mapping[Combo, str],
        grain: str | None,
        correction: str | None,
    ) -> TableRowOut | None:
        """Linha de totais: o recorte, ou o Brasil, com o valor publicado (ou derivado)."""
        target = within or ("brasil:1" if level != "brasil" else None)
        if target is None:
            return None
        try:
            geo = self._gold.geography(ctx, target)
            obs, _ = self._observations(
                ctx,
                kpi,
                level=geo["level_id"],
                within=None,
                periods=(period,),
                dims=dims,
                max_rows=50_000,
                grain=grain,
                correction=correction,
            )
        except (SemanticError, NotFoundError):
            return None  # o KPI não tem o nível do recorte
        cells = {
            keys[o.combo]: CellOut(value=to_float(o.value), status=o.status)
            for o in obs
            if o.geography_key == target and o.combo in keys
        }
        if not cells:
            return None
        return TableRowOut(
            geography_key=target, name=geo["name"], uf_abbreviation=None, cells=cells
        )

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
        grain: str | None = None,
        correction: str | None = None,
    ) -> MapOut:
        """Valor do KPI em cada território do nível: o Total ou, com ``map_share``, o %
        de uma categoria no Total (KPIs cujo Total é só o universo)."""
        kpi = self.kpi(ctx, kpi_id)
        grain = self._grain(ctx, kpi, grain)
        chosen = self._period(ctx, kpi, period, grain)
        meta = self._gold.indicators(ctx)[kpi.indicator]
        if kpi.map_share is not None:
            return self._share_map(ctx, kpi, level=level, period=chosen, within=within)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=(chosen,),
            dims=(),
            max_rows=50_000,
            grain=grain,
            correction=correction,
        )
        return MapOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            level=level,
            period=chosen,
            grain=grain,
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

    def _share_map(
        self, ctx: ReleaseContext, kpi: KpiConfig, *, level: str, period: str, within: str | None
    ) -> MapOut:
        """Participação (%) da categoria ``map_share`` no Total da primeira dimensão."""
        dim = kpi.dimensions[0].classification
        total_key = self._gold.total_category(ctx, dim)["category_key"]
        share_key = f"{dim}:{kpi.map_share}"
        if share_key not in self._gold.categories(ctx):
            msg = f"{kpi.id}: categoria {kpi.map_share} inexistente em {dim}"
            raise PortalConfigError(msg)
        obs, prov = self._observations(
            ctx, kpi, level=level, within=within, periods=(period,), dims=(dim,), max_rows=200_000
        )
        totals = {o.geography_key: o for o in obs if o.combo == (total_key,)}
        parts = {o.geography_key: o for o in obs if o.combo == (share_key,)}
        values = []
        for key, total in totals.items():
            part = parts.get(key)
            share: float | None = None
            status = total.status
            if part is None:
                status = "absent"
            elif part.value is not None and total.value:
                share = round(float(part.value) / float(total.value) * 100, 2)
            else:
                status = part.status if part.value is None else total.status
            values.append(
                MapValueOut(geography_key=key, name=total.name, value=share, status=status)
            )
        name = self._gold.categories(ctx)[share_key]["name"]
        return MapOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            level=level,
            period=period,
            unit="%",
            additivity="non_additive",
            measure="share",
            measure_label=f"% {name}",
            values=values,
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
        grain: str | None = None,
        correction: str | None = None,
    ) -> DetailOut:
        """Sub-KPIs aninhados de um território (tooltip)."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        grain = self._grain(ctx, kpi, grain)
        chosen = self._period(ctx, kpi, period, grain)
        ref = self._ref(ctx, geography)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=ref.level_id,
            within=geography,
            periods=(chosen,),
            dims=dims,
            max_rows=10_000,
            grain=grain,
            correction=correction,
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
                    sub = node(tuple(child), depth + 1, found)
                    # Categoria sem nenhuma observação no período (ex.: faixa de
                    # rendimento de outra edição da POF) não aparece (ADR-0016).
                    if sub.status != "absent" or sub.children:
                        children.append(sub)
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
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        geography: str,
        dimensions: Sequence[str],
        grain: str | None = None,
        correction: str | None = None,
    ) -> SeriesOut:
        """Todos os períodos de um território, por combinação de categorias."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        grain = self._grain(ctx, kpi, grain)
        ref = self._ref(ctx, geography)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=ref.level_id,
            within=geography,
            periods=(),
            dims=dims,
            max_rows=50_000,
            grain=grain,
            correction=correction,
        )
        by_combo: dict[Combo, list[Observation]] = {}
        for o in obs:
            if o.geography_key == geography:
                by_combo.setdefault(o.combo, []).append(o)
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        series = [
            SeriesItemOut(
                key="|".join(combo) or "total",
                label=self._label(ctx, combo, dims),
                categories=dict(zip(dims, combo, strict=True)),
                depth=sum(c != t for c, t in zip(combo, totals, strict=True)),
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
            grain=grain,
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
        grain: str | None = None,
        correction: str | None = None,
    ) -> TableOut:
        """Territórios do nível, com o Total e as combinações de categorias.

        ``locate``: a página devolvida é a que contém esse território, na mesma
        ordenação (o portal localiza na tabela o território clicado no mapa). Se
        ele não estiver na tabela, vale ``offset``.
        """
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        grain = self._grain(ctx, kpi, grain)
        chosen = self._period(ctx, kpi, period, grain)
        limit = min(limit, self._page_max)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=(chosen,),
            dims=dims,
            max_rows=200_000,
            grain=grain,
            correction=correction,
        )
        combos = self._combos(ctx, kpi, dims, row_totals=True)
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        keys = {c: "|".join(c) or "total" for c in combos}

        def parent(c: Combo) -> str | None:
            # A mesma combinação com a última categoria detalhada trocada pelo Total.
            last = max(
                (i for i, (k, t) in enumerate(zip(c, totals, strict=True)) if k != t), default=None
            )
            if last is None:
                return None
            return keys.get((*c[:last], totals[last], *c[last + 1 :]))

        def group(c: Combo) -> str:
            return keys[(c[0], *totals[1:])] if c else keys[c]

        grid: dict[str, dict[str, Any]] = {}
        for o in obs:
            row = grid.setdefault(o.geography_key, {"name": o.name, "cells": {}})
            if o.combo in keys:
                row["cells"][keys[o.combo]] = CellOut(value=to_float(o.value), status=o.status)
        total_key = keys[combos[0]]
        # Colunas só das combinações com alguma observação no período (o Total sempre).
        observed = {o.combo for o in obs}
        combos = [c for i, c in enumerate(combos) if i == 0 or c in observed]

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
            grain=grain,
            unit=meta["unit"],
            columns=[
                ColumnOut(
                    key=keys[c],
                    label=self._label(ctx, c, dims),
                    depth=self._depth(c, totals),
                    group=group(c),
                    parent=parent(c),
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
            footer=self._footer(
                ctx,
                kpi,
                level=level,
                within=within,
                period=chosen,
                dims=dims,
                keys={c: keys[c] for c in combos},
                grain=grain,
                correction=correction,
            ),
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
        grain: str | None = None,
        correction: str | None = None,
    ) -> tuple[KpiConfig, list[str], list[Observation], Provenance]:
        """Observações para exportação (formato longo)."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions)
        grain = self._grain(ctx, kpi, grain)
        for p in periods:
            self._period(ctx, kpi, p, grain)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=periods,
            dims=dims,
            max_rows=max_rows + 1,
            grain=grain,
            correction=correction,
        )
        return kpi, dims, obs, prov


def _price_base(period: str) -> str:
    """Rótulo do período-base dos preços: "jan/2018", "T2 2026" ou "2024"."""
    p = parse_period(period)
    if p.grain == "mes":
        return f"{MONTH_SHORT[p.first_month - 1]}/{p.year}"
    return p.short_label


def reference_months(corr: CorrectionConfig, period: str) -> list[str]:
    """Meses cujo índice vale para o período (ADR-0020); vazio se não houver."""
    if corr.reference == "months":
        month = corr.reference_months.get(period)
        return [month] if month else []
    try:
        return months_of(period)
    except PeriodError:
        return []


def index_level(
    corr: CorrectionConfig, chain: Mapping[str, Decimal], period: str
) -> Decimal | None:
    """Índice do período: o do mês, ou a média dos meses (todos precisam existir)."""
    wanted = reference_months(corr, period)
    got = [chain[m] for m in wanted if m in chain]
    if not wanted or len(got) < len(wanted):
        return None
    return sum(got, Decimal(0)) / len(got)


def correction_base(
    corr: CorrectionConfig, general: Mapping[str, Decimal], periods: Iterable[str]
) -> str | None:
    """Período-base: o mais recente do KPI que o índice geral cobre (avança sozinho)."""
    covered = [p for p in periods if index_level(corr, general, p) is not None]
    return max(covered, key=lambda p: (parse_period(p).end, p)) if covered else None
