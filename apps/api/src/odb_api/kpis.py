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

import json
import logging
import threading
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
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
    HistoryOut,
    HistoryRowOut,
    KpiIndexOut,
    KpiOut,
    KpiSourceOut,
    MapOut,
    MapValueOut,
    NavigationOut,
    PivotFieldOut,
    PivotHeaderOut,
    PivotOut,
    PlannedKpiOut,
    PointOut,
    PortalIndexOut,
    Provenance,
    SeriesItemOut,
    SeriesOut,
    SourceTableOut,
    SubthemeIndexOut,
    SubthemeOut,
    TableOut,
    TableRowOut,
    TableVersionOut,
    ThemeIndexOut,
    ThemeOut,
    TimeGrainOut,
)
from odb_semantics import (
    IndicatorQuery,
    Panorama,
    QueryPlan,
    SemanticError,
    check_against_portal,
    plan_query,
    resolve_links,
)
from odb_semantics.periods import (
    ACCUMULABLE,
    GRAIN_LABELS,
    MONTH_SHORT,
    PeriodError,
    accumulate,
    ancestor,
    complete_periods_at,
    covers,
    months_of,
    parse_period,
    periods_at,
    running,
)
from odb_semantics.portal import (
    CorrectionConfig,
    DimensionConfig,
    KpiConfig,
    PortalConfig,
    PortalConfigError,
    ShortLabels,
    allows_category_shares,
    describe_problems,
    release_problems,
)

logger = logging.getLogger(__name__)

Combo = tuple[str, ...]


# Filtro de categorias (Detalhar por, DS 2.4): dimensão → chaves escolhidas.
Selection = Mapping[str, frozenset[str]]
QUANTITATIVE = frozenset({"valid", "rounded_zero", "true_zero", "derived_sum", "partial_sum"})
SKIPPABLE = frozenset({"not_available", "absent"})


@dataclass(frozen=True, slots=True)
class Observation:
    """Linha de resultado do planejador, já com a combinação de categorias."""

    geography_key: str
    name: str
    period: str
    combo: Combo
    value: Decimal | None
    status: str
    # Tabela de origem (séries compostas, ADR-0022: a fonte pode mudar no tempo).
    source: str | None = None


def _sum_parts(parts: Sequence[Observation]) -> tuple[Decimal | None, str]:
    """Soma das categorias escolhidas: sem as não pesquisadas ("..."), bloqueada por
    sigilo ou outro estado sem valor; somas regionais derivadas preservam subtotais.

    Na região derivada, um detalhe indisponível não esconde os outros escolhidos:
    a decisão do mantenedor de 2026-11-16 exige mostrar o subtotal como parcial.
    """
    values = [p.value for p in parts if p.value is not None]
    regional = any(
        p.geography_key.startswith("regiao:")
        and p.status in {"derived_sum", "partial_sum", "incomplete_sum"}
        for p in parts
    )
    partial = any(p.status == "partial_sum" for p in parts)
    if regional and values and (len(values) < len(parts) or partial):
        return sum(values, Decimal(0)), "partial_sum"
    blocking = [p for p in parts if p.value is None and p.status not in SKIPPABLE]
    if blocking:
        return None, blocking[0].status
    if not values:
        return None, "not_available"
    status = "partial_sum" if partial else "derived_sum"
    return sum(values, Decimal(0)), status


def filter_totals(
    obs: Sequence[Observation],
    dims: Sequence[str],
    selected: Selection,
    totals: Mapping[str, str],
) -> list[Observation]:
    """Total de cada dimensão filtrada = soma das categorias escolhidas (DS 2.4).

    Uma dimensão por vez, na ordem de ``dims``: com cruzamentos, o Total de A soma as
    linhas (A escolhida, B) já recalculadas para B. Só para indicadores somáveis.
    """
    out = list(obs)
    for i, dim in enumerate(dims):
        chosen = selected.get(dim)
        if not chosen:
            continue
        groups: dict[tuple[str, str, Combo], list[Observation]] = {}
        for o in out:
            if o.combo[i] in chosen:
                rest = o.combo[:i] + o.combo[i + 1 :]
                groups.setdefault((o.geography_key, o.period, rest), []).append(o)
        recomputed = []
        for o in out:
            if o.combo[i] == totals[dim]:
                parts = groups.get((o.geography_key, o.period, o.combo[:i] + o.combo[i + 1 :]), [])
                value, status = _sum_parts(parts)
                o = replace(o, value=value, status=status)  # noqa: PLW2901
            recomputed.append(o)
        out = recomputed
    return out


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


_SEP = " › "  # noqa: RUF001 - separador de exibição (período, categoria)

# Teto de células da tabela dinâmica (B6): o navegador desenha a tabela inteira.
PIVOT_MAX_CELLS = 60_000

# Teto de períodos numa consulta com vários períodos (tabela, acumulado): 10 anos de meses.
MAX_PERIODS = 120


class PivotTooLargeError(SemanticError):
    """Recusa determinística do pivot, vinculada ao release realmente consultado."""

    def __init__(self, release_id: str, message: str) -> None:
        super().__init__(message)
        self.release_id = release_id


def _pivot_limit_message() -> str:
    """Preserva a mensagem da recusa anterior à contagem real."""
    return (
        f"tabela dinâmica grande demais (mais de {PIVOT_MAX_CELLS} células): "
        "escolha um nível maior, um recorte ou menos campos"
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
        labels: ShortLabels | None = None,
        table_links: Mapping[str, str] | None = None,
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
        self._short = labels or ShortLabels()
        self._panorama = panorama
        self._page_max = page_max
        # dataset → (sigla da instituição, sistema), das fontes configuradas.
        self._provenance = dict(provenance or {})
        # tabela de origem → link oficial (``reference_url`` das fontes configuradas).
        self._table_links = dict(table_links or {})
        # (release, indicador do índice) → grupo → mês → índice encadeado (ADR-0020).
        self._indexes: dict[tuple[str, str], dict[str, dict[str, Decimal]]] = {}
        # release → KPIs com problema contra ele (ADR-0015).
        self._unavailable: dict[str, dict[str, list[str]]] = {}
        # release → navegação e cada KPI já serializados (só mudam com o release).
        self._serialized: dict[str, tuple[bytes, dict[str, bytes], bytes]] = {}
        self._serialized_lock = threading.Lock()

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

    def _dims(
        self, kpi: KpiConfig, requested: Sequence[str], level: str | None = None
    ) -> list[str]:
        """Dimensões pedidas, na ordem do portal. ``level``: nível da consulta (C1)."""
        exposed = [d.classification for d in kpi.dimensions]
        unknown = [d for d in requested if d not in exposed]
        if unknown:
            msg = f"{kpi.id}: dimensões não disponíveis {unknown} (disponíveis: {exposed})"
            raise SemanticError(msg)
        chosen = [d for d in exposed if d in set(requested)]  # ordem do portal, sem repetição
        if kpi.exclusive_dimensions and len(chosen) > 1 and not kpi.can_cross(chosen, level):
            where = (
                f" (cruzamentos só em {', '.join(kpi.crossed_levels)})"
                if kpi.crossed_levels
                else ""
            )
            msg = (
                f"{kpi.id}: detalhe uma dimensão por vez (cada uma vem com as demais no Total,"
                f" sem os cruzamentos){where}"
            )
            raise SemanticError(msg)
        return chosen

    def _dimension_out(
        self, ctx: ReleaseContext, kpi: KpiConfig, levels: Sequence[str]
    ) -> list[DimensionOut]:
        coverage = self._gold.coverage(ctx).get(kpi.indicator, {})
        # Níveis gravados no release (os derivados na consulta não entram: sem restrição).
        stored = set().union(*(t["levels"] for t in coverage.values())) if coverage else set()
        out = []
        for dim in kpi.dimensions:
            cats = self._gold.partition_categories(ctx, dim.classification, dim.partition)
            tables = sorted(
                t for t, v in coverage.items() if dim.classification in v["classifications"]
            )
            covered = set().union(
                *(coverage[t]["classifications"][dim.classification] for t in tables)
            )
            # Detalhe ausente num nível gravado (ex.: estado civil sem município no
            # release): o portal desativa a opção e avisa, em vez de mostrar só o Total.
            missing = (stored - covered) if tables else set()
            dim_levels = list(dim.levels) or (
                [lvl for lvl in levels if lvl not in missing] if missing else []
            )
            out.append(
                DimensionOut(
                    classification_id=dim.classification,
                    label=self._short.dimension(dim.classification) or dim.label,
                    full_label=dim.label,
                    partition_id=dim.partition,
                    levels=dim_levels,
                    source_table_ids=tables,
                    total_category_key=self._gold.total_category(ctx, dim.classification)[
                        "category_key"
                    ],
                    categories=[
                        CategoryOut(
                            category_key=c["category_key"],
                            category_id=c["category_id"],
                            name=self._name(ctx, c["category_key"]),
                            full_name=c["name"],
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
            category_shares=allows_category_shares(str(meta["unit"]), str(meta["additivity"])),
            periods=list(meta["periods"] or ()),
            periods_by_level=self._gold.periods_by_level(ctx).get(kpi.indicator, {}),
            levels=levels,
            map_levels=[
                lvl
                for lvl in levels
                if lvl in geometry and (kpi.map_levels is None or lvl in kpi.map_levels)
            ],
            dimensions=self._dimension_out(ctx, kpi, levels),
            exclusive_dimensions=kpi.exclusive_dimensions,
            crossed=[list(g) for g in kpi.crossed],
            crossed_levels=list(kpi.crossed_levels),
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
                tables=self._source_tables(ctx, kpi, meta),
            ),
        )

    def _source_tables(
        self, ctx: ReleaseContext, kpi: KpiConfig, meta: Mapping[str, Any]
    ) -> list[SourceTableOut]:
        """Tabelas de origem do KPI no release, a principal primeiro (DS 2.9)."""
        main = str(meta["source_table_id"])
        coverage = self._gold.coverage(ctx).get(kpi.indicator, {})
        exposed = {d.classification for d in kpi.dimensions}
        tables = sorted(coverage, key=lambda t: (t != main, t))
        return [
            SourceTableOut(
                table_id=t,
                reference_url=self._table_links.get(t)
                or (meta.get("reference_url") if t == main else None),
                classification_ids=sorted(
                    c for c in coverage[t]["classifications"] if c in exposed
                ),
                periods=sorted(coverage[t]["periods"], key=lambda p: (parse_period(p).start, p)),
            )
            for t in tables
        ]

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

    def serialized(self, ctx: ReleaseContext) -> tuple[bytes, dict[str, bytes]]:
        """Navegação completa e metadados de cada KPI, preservando o contrato existente."""
        navigation, kpis, _ = self._serialize(ctx)
        return navigation, kpis

    def serialized_index(self, ctx: ReleaseContext) -> bytes:
        """Índice leve montado junto da navegação, uma vez por release (Plano D, D1)."""
        return self._serialize(ctx)[2]

    def _serialize(self, ctx: ReleaseContext) -> tuple[bytes, dict[str, bytes], bytes]:
        """Navegação e KPIs do release em JSON, montados uma vez por release.

        Achado da homologação (V5): montar a navegação custava ~8 s de CPU sob carga e
        acontecia em toda página do portal e em todo ``/kpis/{id}``. O resultado só
        depende do release e da configuração (fixa no processo). A trava evita que
        várias requisições simultâneas montem o mesmo release ao mesmo tempo.
        """
        found = self._serialized.get(ctx.release_id)
        if found is not None:
            return found
        with self._serialized_lock:
            found = self._serialized.get(ctx.release_id)
            if found is None:
                nav = self.navigation(ctx)
                kpis = {
                    item.kpi_id: _json(item)
                    for theme in nav.themes
                    for sub in theme.subthemes
                    for item in sub.kpis
                }
                index = PortalIndexOut(
                    release_id=nav.release_id,
                    scope=nav.scope,
                    dimension_order=nav.dimension_order,
                    themes=[
                        ThemeIndexOut(
                            theme_id=theme.theme_id,
                            label=theme.label,
                            filters=theme.filters,
                            subthemes=[
                                SubthemeIndexOut(
                                    subtheme_id=sub.subtheme_id,
                                    label=sub.label,
                                    planned=sub.planned,
                                    kpis=[
                                        KpiIndexOut(
                                            kpi_id=item.kpi_id,
                                            label=item.label,
                                            name=item.name,
                                            description=item.description,
                                            source_table_id=item.source.source_table_id,
                                        )
                                        for item in sub.kpis
                                    ],
                                )
                                for sub in theme.subthemes
                            ],
                        )
                        for theme in nav.themes
                    ],
                )
                found = (_json(nav), kpis, _json(index))
                # Guarda só o release atual e o anterior (rollback e troca de release).
                for old in list(self._serialized)[:-1]:
                    del self._serialized[old]
                self._serialized[ctx.release_id] = found
        return found

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
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        period: str | None,
        grain: str | None = None,
        level: str | None = None,
    ) -> str:
        """Período publicado no nível e grão; sem pedido, o último completo disponível."""
        base: list[str] = list(self._gold.indicators(ctx)[kpi.indicator]["periods"] or ())
        if level is not None:
            base = self._gold.periods_by_level(ctx).get(kpi.indicator, {}).get(level, base)
        periods = periods_at(base, grain) if grain else base
        if period is None:
            if not periods:
                msg = f"{kpi.indicator} sem períodos publicados"
                raise NotFoundError(msg)
            complete = complete_periods_at(base, grain) if grain else periods
            return (complete or periods)[-1]
        if period not in periods:
            where = f" no nível {level}" if level else ""
            msg = f"{kpi.indicator} não tem o período {period}{where} (disponíveis: {periods})"
            raise SemanticError(msg)
        return period

    # ------------------------------------------------- vários períodos e acumulado (ADR-0026)

    def _rule(self, ctx: ReleaseContext, kpi: KpiConfig) -> str:
        """Regra para acumular períodos: soma (fluxos) ou composição (variações %)."""
        meta = self._gold.indicators(ctx)[kpi.indicator]
        rule = meta.get("time_aggregation") if len(meta.get("time_grains") or ()) > 1 else None
        if rule not in ACCUMULABLE or kpi.map_share is not None:
            msg = (
                f"{kpi.id}: acumular períodos só vale para fluxos (soma) e variações % "
                "(composição); taxas, médias e índices não acumulam"
            )
            raise SemanticError(msg)
        return str(rule)

    def _window(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        periods: Sequence[str],
        grain: str | None,
        level: str | None,
    ) -> list[str]:
        """Períodos pedidos, validados no grão e no nível, em ordem; sem pedido, o padrão."""
        if len(periods) > MAX_PERIODS:
            msg = f"no máximo {MAX_PERIODS} períodos por consulta"
            raise SemanticError(msg)
        chosen = {self._period(ctx, kpi, p, grain, level) for p in periods}
        if not chosen:
            chosen = {self._period(ctx, kpi, None, grain, level)}
        return sorted(chosen, key=lambda p: (parse_period(p).start, p))

    @staticmethod
    def _accumulated(
        obs: Sequence[Observation], periods: Sequence[str], mode: str, rule: str
    ) -> list[Observation]:
        """Acumula as observações de cada território e combinação nos ``periods``.

        ``total``: um valor só (rotulado com o último período); ``running``: acumulado
        corrente; ``year``: acumulado no ano. Período sem observação conta como lacuna.
        """
        groups: dict[tuple[str, Combo], dict[str, Observation]] = {}
        for o in obs:
            groups.setdefault((o.geography_key, o.combo), {})[o.period] = o
        out: list[Observation] = []
        for (geo, combo), found in groups.items():
            sample = next(iter(found.values()))
            items = [
                (p, found[p].value, found[p].status) if p in found else (p, None, "absent")
                for p in periods
            ]
            if mode == "total":
                value, status = accumulate([(v, st) for _, v, st in items], rule)
                acc = [(periods[-1], value, status)]
            else:
                acc = running(items, rule, by_year=mode == "year")
            out.extend(
                Observation(
                    geography_key=geo,
                    name=sample.name,
                    period=p,
                    combo=combo,
                    value=v,
                    status=st,
                    source=sample.source,
                )
                for p, v, st in acc
            )
        return out

    def _selection(
        self, ctx: ReleaseContext, kpi: KpiConfig, categories: Sequence[str]
    ) -> dict[str, frozenset[str]]:
        """Filtro de categorias validado: só categorias expostas; a escolha de todas
        as categorias de uma dimensão é o mesmo que nenhum filtro."""
        if not categories:
            return {}
        chosen: dict[str, set[str]] = {}
        every: dict[str, set[str]] = {}
        for key in categories:
            dim = key.split(":", 1)[0]
            cfg = next((d for d in kpi.dimensions if d.classification == dim), None)
            if cfg is not None and dim not in every:
                cats = self._gold.partition_categories(ctx, dim, cfg.partition)
                every[dim] = {c["category_key"] for c in cats}
            if key not in every.get(dim, set()):
                msg = f"{kpi.id}: categoria {key} fora das dimensões expostas do KPI"
                raise SemanticError(msg)
            chosen.setdefault(dim, set()).add(key)
        return {dim: frozenset(keys) for dim, keys in chosen.items() if keys != every[dim]}

    def _partition(
        self, ctx: ReleaseContext, dim: DimensionConfig, selected: Selection | None
    ) -> list[Mapping[str, Any]]:
        """Categorias da partição exposta, só as escolhidas quando há filtro."""
        cats = self._gold.partition_categories(ctx, dim.classification, dim.partition)
        chosen = (selected or {}).get(dim.classification)
        return [c for c in cats if c["category_key"] in chosen] if chosen else list(cats)

    def _breakdown(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        dims: Sequence[str],
        selected: Selection | None = None,
    ) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        for dim in kpi.dimensions:
            if dim.classification in dims:
                total = self._gold.total_category(ctx, dim.classification)["category_id"]
                cats = self._partition(ctx, dim, selected)
                out[dim.classification] = (total, *(c["category_id"] for c in cats))
        return out

    def _observation_plan(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        *,
        level: str,
        within: str | None,
        periods: Sequence[str],
        dims: Sequence[str],
        grain: str | None,
        selected: Selection | None,
    ) -> tuple[QueryPlan, list[str], list[str]]:
        """Plano comum à leitura e à contagem real de observações (Plano D, D4)."""
        sel = dict(selected or {})
        extra = [
            d.classification
            for d in kpi.dimensions
            if d.classification in sel and d.classification not in dims
        ]
        query_dims = [*dims, *extra]
        partial = None
        if grain:
            # O período do grão em andamento (contém o último publicado) sai parcial.
            published = list(self._gold.indicators(ctx)[kpi.indicator]["periods"] or ())
            if published:
                last = max(published, key=lambda p: (parse_period(p).end, p))
                current = ancestor(last, grain)
                if current not in complete_periods_at(published, grain):
                    partial = current
        query = IndicatorQuery(
            indicators=(kpi.indicator,),
            level=level,
            within=within,
            periods=tuple(periods),
            breakdown=self._breakdown(ctx, kpi, query_dims, sel),
            grain=grain,
            partial_period=partial,
        )
        plan = plan_query(query, self._gold.indicator_meta(ctx))
        return plan, query_dims, extra

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
        selected: Selection | None = None,
        for_export: bool = False,
    ) -> tuple[list[Observation], Provenance]:
        """Observações do KPI. Com filtro de categorias, as dimensões filtradas entram na
        consulta (mesmo fora de ``dims``), o Total delas vira a soma das escolhidas
        (indicadores somáveis) e o resultado volta às combinações de ``dims``."""
        sel = dict(selected or {})
        plan, query_dims, extra = self._observation_plan(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=periods,
            dims=dims,
            grain=grain,
            selected=sel,
        )
        result = self._gold.run_plan(ctx, plan, max_rows=max_rows, for_export=for_export)
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
                    combo=tuple(parts[d] for d in query_dims),
                    value=row["value"],
                    status=row["value_status"],
                    source=row.get("source_table_id"),
                )
            )
        prov = provenance(
            ctx, plan.aliases.values(), derived=plan.derived, truncated=result.truncated
        )
        if correction:
            out, prov = self._corrected(ctx, kpi, correction, out, dims=query_dims, prov=prov)
        if sel:
            totals = {d: self._gold.total_category(ctx, d)["category_key"] for d in query_dims}
            meta = self._gold.indicators(ctx)[kpi.indicator]
            if allows_category_shares(str(meta["unit"]), str(meta["additivity"])):
                out = filter_totals(out, query_dims, sel, totals)
            if extra:
                n = len(dims)
                out = [
                    replace(o, combo=o.combo[:n])
                    for o in out
                    if all(o.combo[n + k] == totals[d] for k, d in enumerate(extra))
                ]
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
            out.append(
                Observation(o.geography_key, o.name, o.period, o.combo, value, status, o.source)
            )
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
        selected: Selection | None = None,
    ) -> list[Combo]:
        """Combinações em pré-ordem: Total, depois cada categoria e seus filhos.

        ``row_totals``: com duas ou mais dimensões, também o Total da primeira cruzado com
        as demais (Total e Homens), logo depois do Total: os totais de linha da matriz.
        """
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        cats = {
            d.classification: [c["category_key"] for c in self._partition(ctx, d, selected)]
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
        selected: Selection | None = None,
        window: Sequence[str] = (),
        accumulate: str | None = None,
        rule: str | None = None,
    ) -> TableRowOut | None:
        """Linha de totais: o recorte, ou o Brasil, com o valor publicado (ou derivado).

        Com ``window`` (vários períodos), as chaves das células levam o período
        (``período~combinação``), salvo no acumulado total, que tem uma coluna só."""
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
                periods=tuple(window or (period,)),
                dims=dims,
                max_rows=50_000 * max(1, len(window)),
                grain=grain,
                correction=correction,
                selected=selected,
            )
        except (SemanticError, NotFoundError):
            return None  # o KPI não tem o nível do recorte
        obs = [o for o in obs if o.geography_key == target]
        if accumulate and rule:
            obs = self._accumulated(obs, window, accumulate, rule)
        multi = len(window) > 1 and accumulate != "total"
        cells = {
            (f"{o.period}~{keys[o.combo]}" if multi else keys[o.combo]): CellOut(
                value=to_float(o.value), status=o.status
            )
            for o in obs
            if o.combo in keys
        }
        if not cells:
            return None
        return TableRowOut(
            geography_key=target, name=geo["name"], uf_abbreviation=None, cells=cells
        )

    def _name(self, ctx: ReleaseContext, key: str) -> str:
        """Rótulo curto da categoria (``rotulos.toml``) ou o nome da Gold."""
        return self._short.category(key) or str(self._gold.categories(ctx)[key]["name"])

    def _label(
        self, ctx: ReleaseContext, combo: Combo, dims: Sequence[str], *, full: bool = False
    ) -> str:
        cats = self._gold.categories(ctx)
        names = [
            str(cats[key]["name"]) if full else self._name(ctx, key)
            for key in combo
            if not cats[key]["is_total"]
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
        categories: Sequence[str] = (),
        periods: Sequence[str] = (),
        accumulate: bool = False,
    ) -> MapOut:
        """Valor do KPI em cada território do nível: o Total ou, com ``map_share``, o %
        de uma categoria no Total (KPIs cujo Total é só o universo).

        ``accumulate``: o acumulado dos ``periods`` (soma ou composição, ADR-0026)."""
        kpi = self.kpi(ctx, kpi_id)
        grain = self._grain(ctx, kpi, grain)
        window: list[str] = []
        if accumulate:
            rule = self._rule(ctx, kpi)
            window = self._window(ctx, kpi, periods or ([period] if period else []), grain, level)
            chosen = window[-1]
        else:
            chosen = self._period(ctx, kpi, period, grain, level)
        meta = self._gold.indicators(ctx)[kpi.indicator]
        sel = self._selection(ctx, kpi, categories)
        if kpi.map_share is not None:
            return self._share_map(
                ctx, kpi, level=level, period=chosen, within=within, selected=sel
            )
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=tuple(window or (chosen,)),
            dims=(),
            max_rows=50_000 * max(1, len(window)),
            grain=grain,
            correction=correction,
            selected=sel,
        )
        if window:
            obs = self._accumulated(obs, window, "total", rule)
        return MapOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            level=level,
            period=chosen,
            periods=window,
            accumulated="total" if window else None,
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
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        *,
        level: str,
        period: str,
        within: str | None,
        selected: Selection | None = None,
    ) -> MapOut:
        """Participação (%) da categoria ``map_share`` no Total da sua dimensão.

        A dimensão é a que contém a categoria (não precisa ser a primeira: no Plano
        Diretor, o detalhe começa pelo tamanho do município, e o mapa pinta o % "Com
        Plano Diretor").
        """
        cats = self._gold.categories(ctx)
        dim = next(
            (
                d.classification
                for d in kpi.dimensions
                if f"{d.classification}:{kpi.map_share}" in cats
            ),
            kpi.dimensions[0].classification,
        )
        total_key = self._gold.total_category(ctx, dim)["category_key"]
        share_key = f"{dim}:{kpi.map_share}"
        if share_key not in self._gold.categories(ctx):
            msg = f"{kpi.id}: categoria {kpi.map_share} inexistente em {dim}"
            raise PortalConfigError(msg)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=(period,),
            dims=(dim,),
            max_rows=200_000,
            selected=selected,
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
                if "partial_sum" in (part.status, total.status):
                    status = "partial_sum"
            else:
                status = part.status if part.value is None else total.status
            values.append(
                MapValueOut(geography_key=key, name=total.name, value=share, status=status)
            )
        name = self._name(ctx, share_key)
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
        categories: Sequence[str] = (),
        periods: Sequence[str] = (),
        accumulate: bool = False,
    ) -> DetailOut:
        """Sub-KPIs aninhados de um território (tooltip); com ``accumulate``, o
        acumulado dos ``periods`` (ADR-0026)."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions, geography.split(":", 1)[0])
        sel = self._selection(ctx, kpi, categories)
        grain = self._grain(ctx, kpi, grain)
        ref = self._ref(ctx, geography)
        window: list[str] = []
        if accumulate:
            rule = self._rule(ctx, kpi)
            window = self._window(
                ctx, kpi, periods or ([period] if period else []), grain, ref.level_id
            )
            chosen = window[-1]
        else:
            chosen = self._period(ctx, kpi, period, grain, ref.level_id)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=ref.level_id,
            within=geography,
            periods=tuple(window or (chosen,)),
            dims=dims,
            max_rows=10_000 * max(1, len(window)),
            grain=grain,
            correction=correction,
            selected=sel,
        )
        if window:
            obs = self._accumulated(obs, window, "total", rule)
        return self._detail_out(
            ctx,
            kpi,
            ref=ref,
            chosen=chosen,
            window=window,
            dims=dims,
            sel=sel,
            obs=obs,
            prov=prov,
        )

    def details(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        level: str,
        within: str | None,
        period: str | None,
        dimensions: Sequence[str],
        grain: str | None = None,
        correction: str | None = None,
        categories: Sequence[str] = (),
        periods: Sequence[str] = (),
        accumulate: bool = False,
    ) -> list[DetailOut]:
        """Detalhes do nível em uma leitura; municípios somente dentro de uma UF (D6)."""
        if level not in {"brasil", "regiao", "uf", "municipio"} or (
            level == "municipio" and (within is None or not within.startswith("uf:"))
        ):
            msg = "detalhes em lote: selecione região, UF ou municípios dentro de uma UF"
            raise SemanticError(msg)
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions, level)
        sel = self._selection(ctx, kpi, categories)
        grain = self._grain(ctx, kpi, grain)
        if within:
            self._ref(ctx, within)
        window: list[str] = []
        if accumulate:
            rule = self._rule(ctx, kpi)
            window = self._window(ctx, kpi, periods or ([period] if period else []), grain, level)
            chosen = window[-1]
        else:
            chosen = self._period(ctx, kpi, period, grain, level)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=tuple(window or (chosen,)),
            dims=dims,
            max_rows=100_000,
            grain=grain,
            correction=correction,
            selected=sel,
        )
        if prov.truncated:
            msg = "detalhes em lote excedem o limite de leitura: reduza períodos ou detalhes"
            raise SemanticError(msg)
        if window:
            obs = self._accumulated(obs, window, "total", rule)
        grouped: dict[str, list[Observation]] = {}
        for item in obs:
            grouped.setdefault(item.geography_key, []).append(item)
        territories = self._gold.search_geographies(
            ctx, text=None, levels=(level,), within=within, limit=50_000
        )
        return [
            self._detail_out(
                ctx,
                kpi,
                ref=GeographyRefOut(
                    geography_key=geo["geography_key"], name=geo["name"], level_id=geo["level_id"]
                ),
                chosen=chosen,
                window=window,
                dims=dims,
                sel=sel,
                obs=grouped.get(geo["geography_key"], []),
                prov=prov,
            )
            for geo in territories
        ]

    def _detail_out(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        *,
        ref: GeographyRefOut,
        chosen: str,
        window: list[str],
        dims: list[str],
        sel: Selection,
        obs: Sequence[Observation],
        prov: Provenance,
    ) -> DetailOut:
        """Monta o mesmo tooltip nas rotas individual e em lote, sem novas consultas."""
        meta = self._gold.indicators(ctx)[kpi.indicator]
        # % das categorias: indicadores somáveis ou de quantidade (DS 2.3.12).
        additive = allows_category_shares(str(meta["unit"]), str(meta["additivity"]))
        values = {o.combo: o for o in obs if o.geography_key == ref.geography_key}
        names = self._gold.categories(ctx)
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
                for cat in self._partition(ctx, dim, sel):
                    child = list(combo)
                    child[depth] = cat["category_key"]
                    sub = node(tuple(child), depth + 1, found)
                    # Categoria sem nenhuma observação no período (ex.: faixa de
                    # rendimento de outra edição da POF) não aparece (ADR-0016).
                    if sub.status != "absent" or sub.children:
                        children.append(sub)
            key = combo[depth - 1] if depth else None
            return DetailNodeOut(
                label=self._name(ctx, key) if key else "Total",
                full_label=str(names[key]["name"]) if key else "Total",
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
            periods=window,
            accumulated="total" if window else None,
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
        categories: Sequence[str] = (),
        periods: Sequence[str] = (),
        accumulate: str | None = None,
    ) -> SeriesOut:
        """Todos os períodos de um território, por combinação de categorias.

        ``periods``: só os pontos contidos nesses períodos (ex.: os anos isolados).
        ``accumulate``: ``running`` (acumulado corrente nos pontos) ou ``year``
        (acumulado no ano), ADR-0026."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions, geography.split(":", 1)[0])
        sel = self._selection(ctx, kpi, categories)
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
            selected=sel,
        )
        if periods:
            for p in periods:
                parse_period(p)  # valida o código
            obs = [o for o in obs if any(covers(p, o.period) for p in periods)]
        if accumulate:
            rule = self._rule(ctx, kpi)
            ordered = sorted({o.period for o in obs}, key=lambda p: (parse_period(p).start, p))
            obs = self._accumulated(obs, ordered, accumulate, rule)
        by_combo: dict[Combo, list[Observation]] = {}
        for o in obs:
            if o.geography_key == geography:
                by_combo.setdefault(o.combo, []).append(o)
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        series = [
            SeriesItemOut(
                key="|".join(combo) or "total",
                label=self._label(ctx, combo, dims),
                full_label=self._label(ctx, combo, dims, full=True),
                categories=dict(zip(dims, combo, strict=True)),
                depth=sum(c != t for c, t in zip(combo, totals, strict=True)),
                points=[
                    PointOut(
                        period=o.period,
                        value=to_float(o.value),
                        status=o.status,
                        source_table_id=o.source,
                    )
                    for o in sorted(by_combo[combo], key=lambda x: x.period)
                ],
            )
            for combo in self._combos(ctx, kpi, dims, selected=sel)
            if combo in by_combo
        ]
        meta = self._gold.indicators(ctx)[kpi.indicator]
        return SeriesOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            geography=ref,
            unit=meta["unit"],
            grain=grain,
            accumulated=accumulate,
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
        categories: Sequence[str] = (),
        periods: Sequence[str] = (),
        accumulate: str | None = None,
    ) -> TableOut:
        """Territórios do nível, com o Total e as combinações de categorias.

        ``periods`` com mais de um período: um grupo de colunas por período (ADR-0026);
        ``accumulate``: ``total`` (uma coluna com o acumulado), ``running`` (acumulado
        corrente) ou ``year`` (acumulado no ano, com "Isolar período").

        ``locate``: a página devolvida é a que contém esse território, na mesma
        ordenação (o portal localiza na tabela o território clicado no mapa). Se
        ele não estiver na tabela, vale ``offset``.
        """
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions, level)
        sel = self._selection(ctx, kpi, categories)
        grain = self._grain(ctx, kpi, grain)
        rule = self._rule(ctx, kpi) if accumulate else None
        window = (
            self._window(ctx, kpi, periods or ([period] if period else []), grain, level)
            if periods or accumulate
            else []
        )
        if len(window) == 1 and not accumulate:
            window = []
        chosen = window[-1] if window else self._period(ctx, kpi, period, grain, level)
        multi = len(window) > 1 and accumulate != "total"
        limit = min(limit, self._page_max)
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=tuple(window or (chosen,)),
            dims=dims,
            max_rows=200_000 * max(1, len(window)),
            grain=grain,
            correction=correction,
            selected=sel,
        )
        if accumulate and rule:
            obs = self._accumulated(obs, window, accumulate, rule)
        combos = self._combos(ctx, kpi, dims, row_totals=True, selected=sel)
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

        def cell_key(o_period: str, combo: Combo) -> str:
            return f"{o_period}~{keys[combo]}" if multi else keys[combo]

        grid: dict[str, dict[str, Any]] = {}
        for o in obs:
            row = grid.setdefault(o.geography_key, {"name": o.name, "cells": {}})
            if o.combo in keys:
                row["cells"][cell_key(o.period, o.combo)] = CellOut(
                    value=to_float(o.value), status=o.status
                )
        # Ordenação pelo Total do último período (o do mapa).
        total_key = cell_key(chosen, combos[0])
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
            periods=window,
            accumulated=accumulate,
            grain=grain,
            unit=meta["unit"],
            columns=(
                [
                    ColumnOut(
                        key=cell_key(p, c),
                        label=_period_label(p)
                        if i == 0
                        else f"{_period_label(p)}{_SEP}{self._label(ctx, c, dims)}",
                        full_label=_period_label(p)
                        if i == 0
                        else f"{_period_label(p)}{_SEP}{self._label(ctx, c, dims, full=True)}",
                        depth=self._depth(c, totals),
                        group=cell_key(p, combos[0]),
                        parent=None if i == 0 else cell_key(p, combos[0]),
                        period=p,
                    )
                    for p in window
                    for i, c in enumerate(combos)
                ]
                if multi
                else [
                    ColumnOut(
                        key=keys[c],
                        label=self._label(ctx, c, dims),
                        full_label=self._label(ctx, c, dims, full=True),
                        depth=self._depth(c, totals),
                        group=group(c),
                        parent=parent(c),
                    )
                    for c in combos
                ]
            ),
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
                selected=sel,
                window=window,
                accumulate=accumulate,
                rule=rule,
            ),
            total_rows=len(ordered),
            offset=offset,
            limit=limit,
            provenance=prov,
        )

    def pivot(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        level: str,
        within: str | None,
        rows: Sequence[str],
        cols: Sequence[str],
        grain: str | None = None,
        correction: str | None = None,
        categories: Sequence[str] = (),
        periods: Sequence[str] = (),
    ) -> PivotOut:
        """Tabela dinâmica (B6): reorganiza as observações publicadas (ou derivadas pela
        regra do KPI) em linhas e colunas. Campos: ``territorio``, ``periodo`` e as
        dimensões do KPI. Dimensões fora das linhas e colunas ficam no Total publicado:
        nada é somado aqui.

        ``periods`` (DS 2.9): só os períodos escolhidos no portal (sem eles, todos).
        Com Território nas linhas, vem também a linha de totais do recorte (ou do
        Brasil), para o "% por coluna" do portal."""
        kpi = self.kpi(ctx, kpi_id)
        fields = [*rows, *cols]
        exposed = {d.classification: d for d in kpi.dimensions}
        bad = [f for f in fields if f not in ("territorio", "periodo") and f not in exposed]
        if bad or len(set(fields)) != len(fields) or not rows or not cols:
            msg = f"{kpi.id}: campos da tabela dinâmica inválidos {bad or fields}"
            raise SemanticError(msg)
        dims = self._dims(kpi, [f for f in fields if f in exposed], level)
        sel = self._selection(ctx, kpi, categories)
        grain = self._grain(ctx, kpi, grain)
        window = tuple(self._window(ctx, kpi, periods, grain, level)) if periods else ()
        # A correção de preços valida cobertura e índices durante a leitura. Mantém-se
        # esse caminho para preservar a precedência de seus erros, sem estimar células.
        if correction is None:
            plan, _, extra = self._observation_plan(
                ctx,
                kpi,
                level=level,
                within=within,
                periods=window,
                dims=dims,
                grain=grain,
                selected=sel,
            )
            totals = [str(self._gold.total_category(ctx, d)["category_key"]) for d in extra]
            if self._gold.count_plan(ctx, plan, total_categories=totals) > PIVOT_MAX_CELLS:
                raise PivotTooLargeError(ctx.release_id, _pivot_limit_message())
        obs, prov = self._observations(
            ctx,
            kpi,
            level=level,
            within=within,
            periods=window,
            dims=dims,
            max_rows=PIVOT_MAX_CELLS + 1,
            grain=grain,
            correction=correction,
            selected=sel,
        )
        if len(obs) > PIVOT_MAX_CELLS:
            raise PivotTooLargeError(ctx.release_id, _pivot_limit_message())
        index = {d: i for i, d in enumerate(dims)}
        order: dict[str, dict[str, int]] = {}
        for d in dims:
            total = self._gold.total_category(ctx, d)["category_key"]
            cats = [total, *(c["category_key"] for c in self._partition(ctx, exposed[d], sel))]
            order[d] = {k: i for i, k in enumerate(cats)}

        def value_of(o: Observation, field: str) -> tuple[str, str]:
            if field == "territorio":
                return o.geography_key, o.name
            if field == "periodo":
                return o.period, _period_label(o.period)
            key = o.combo[index[field]]
            return key, "Total" if order[field].get(key) == 0 else self._name(ctx, key)

        def sort_key(field: str, key: str, label: str) -> tuple[Any, ...]:
            if field == "territorio":
                return (label,)
            if field == "periodo":
                return (parse_period(key).start, key)
            return (order[field].get(key, 10_000), label)

        grid: dict[tuple[tuple[str, ...], tuple[str, ...]], CellOut] = {}
        row_heads: dict[tuple[str, ...], tuple[str, ...]] = {}
        col_heads: dict[tuple[str, ...], tuple[str, ...]] = {}
        for o in obs:
            rk = [value_of(o, f) for f in rows]
            ck = [value_of(o, f) for f in cols]
            rkey, ckey = tuple(k for k, _ in rk), tuple(k for k, _ in ck)
            row_heads[rkey] = tuple(lbl for _, lbl in rk)
            col_heads[ckey] = tuple(lbl for _, lbl in ck)
            grid[(rkey, ckey)] = CellOut(value=to_float(o.value), status=o.status)

        def ordered(
            heads: dict[tuple[str, ...], tuple[str, ...]], names: Sequence[str]
        ) -> list[tuple[str, ...]]:
            return sorted(
                heads,
                key=lambda k: tuple(sort_key(f, k[i], heads[k][i]) for i, f in enumerate(names)),
            )

        row_keys, col_keys = ordered(row_heads, rows), ordered(col_heads, cols)
        if len(row_keys) * len(col_keys) > PIVOT_MAX_CELLS:
            msg = f"tabela dinâmica grande demais (mais de {PIVOT_MAX_CELLS} células)"
            raise PivotTooLargeError(ctx.release_id, msg)

        def field_out(f: str) -> PivotFieldOut:
            label = {"territorio": "Território", "periodo": "Período"}.get(f)
            return PivotFieldOut(id=f, label=label or exposed[f].label)

        footer, footer_cells = (
            self._pivot_footer(
                ctx,
                kpi,
                level=level,
                within=within,
                window=window,
                dims=dims,
                grain=grain,
                correction=correction,
                selected=sel,
                key_of=lambda o: tuple(value_of(o, f)[0] for f in cols),
                col_keys=col_keys,
            )
            if list(rows) == ["territorio"]
            else (None, [])
        )

        meta = self._gold.indicators(ctx)[kpi.indicator]
        return PivotOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            level=level,
            grain=grain,
            unit=meta["unit"],
            row_fields=[field_out(f) for f in rows],
            col_fields=[field_out(f) for f in cols],
            rows=[PivotHeaderOut(keys=list(k), labels=list(row_heads[k])) for k in row_keys],
            columns=[PivotHeaderOut(keys=list(k), labels=list(col_heads[k])) for k in col_keys],
            cells=[[grid.get((r, c)) for c in col_keys] for r in row_keys],
            footer=footer,
            footer_cells=footer_cells,
            provenance=prov,
        )

    def _pivot_footer(
        self,
        ctx: ReleaseContext,
        kpi: KpiConfig,
        *,
        level: str,
        within: str | None,
        window: Sequence[str],
        dims: Sequence[str],
        grain: str | None,
        correction: str | None,
        selected: Selection,
        key_of: Callable[[Observation], tuple[str, ...]],
        col_keys: Sequence[tuple[str, ...]],
    ) -> tuple[PivotHeaderOut | None, list[CellOut | None]]:
        """Linha de totais da dinâmica: o recorte, ou o Brasil, nas mesmas colunas."""
        target = within or ("brasil:1" if level != "brasil" else None)
        if target is None:
            return None, []
        try:
            geo = self._gold.geography(ctx, target)
            totals, _ = self._observations(
                ctx,
                kpi,
                level=geo["level_id"],
                within=None,
                periods=window,
                dims=dims,
                max_rows=PIVOT_MAX_CELLS + 1,
                grain=grain,
                correction=correction,
                selected=selected,
            )
        except (SemanticError, NotFoundError):
            return None, []  # o KPI não tem o nível do recorte
        cells = {
            key_of(o): CellOut(value=to_float(o.value), status=o.status)
            for o in totals
            if o.geography_key == target
        }
        if not cells:
            return None, []
        return PivotHeaderOut(keys=[target], labels=[str(geo["name"])]), [
            cells.get(c) for c in col_keys
        ]

    def published_grain(self, ctx: ReleaseContext, kpi_id: str) -> str | None:
        """Grão publicado do KPI (o primeiro de ``time_grains``); None sem grãos."""
        kpi = self.kpi(ctx, kpi_id)
        grains = self._gold.indicators(ctx)[kpi.indicator].get("time_grains") or ()
        return str(grains[0]) if grains else None

    def history(
        self,
        ctx: ReleaseContext,
        kpi_id: str,
        *,
        geography: str,
        dimensions: Sequence[str],
        grains: Sequence[str] = (),
        correction: str | None = None,
        categories: Sequence[str] = (),
    ) -> HistoryOut:
        """Série completa de um território em todos os grãos pedidos (B5).

        Linhas: um período por linha, do ano mais recente ao mais antigo e, dentro do
        ano, do grão maior ao menor (Ano, Semestre, Trimestre, Mês). Os grãos além do
        publicado são derivados pela regra do KPI (ADR-0013) e vêm marcados. Nunca
        acumulado (ADR-0026).
        """
        kpi = self.kpi(ctx, kpi_id)
        ref = self._ref(ctx, geography)
        dims = self._dims(kpi, dimensions, ref.level_id)
        sel = self._selection(ctx, kpi, categories)
        meta = self._gold.indicators(ctx)[kpi.indicator]
        available = [str(g) for g in meta.get("time_grains") or ()]
        wanted: list[str | None] = [g for g in (grains or available) if g in available] or [None]
        combos = self._combos(ctx, kpi, dims, row_totals=True, selected=sel)
        totals = [self._gold.total_category(ctx, d)["category_key"] for d in dims]
        keys = {c: "|".join(c) or "total" for c in combos}
        rows: list[HistoryRowOut] = []
        observed: set[Combo] = set()
        prov: Provenance | None = None
        for wanted_grain in wanted:
            grain = self._grain(ctx, kpi, wanted_grain)
            obs, got = self._observations(
                ctx,
                kpi,
                level=ref.level_id,
                within=geography,
                periods=(),
                dims=dims,
                max_rows=200_000,
                grain=grain,
                correction=correction,
                selected=sel,
            )
            prov = prov or got
            by_period: dict[str, dict[str, CellOut]] = {}
            for o in obs:
                if o.geography_key != geography or o.combo not in keys:
                    continue
                observed.add(o.combo)
                by_period.setdefault(o.period, {})[keys[o.combo]] = CellOut(
                    value=to_float(o.value), status=o.status
                )
            rows.extend(
                HistoryRowOut(
                    period=p,
                    grain=parse_period(p).grain,
                    label=_period_label(p),
                    derived=grain is not None,
                    cells=cells,
                )
                for p, cells in by_period.items()
            )
        order = {"ano": 0, "semestre": 1, "trimestre": 2, "mes": 3}
        rows.sort(
            key=lambda r: (
                -parse_period(r.period).year,
                order[r.grain],
                parse_period(r.period).start,
            )
        )
        combos = [c for i, c in enumerate(combos) if i == 0 or c in observed]
        if prov is None:  # pragma: no cover - sempre há ao menos um grão
            msg = f"{kpi.id} sem observações"
            raise NotFoundError(msg)
        return HistoryOut(
            kpi_id=kpi.id,
            indicator_id=kpi.indicator,
            geography=ref,
            unit=meta["unit"],
            grains=[g or (parse_period(rows[0].period).grain if rows else "") for g in wanted],
            columns=[
                ColumnOut(
                    key=keys[c],
                    label=self._label(ctx, c, dims),
                    full_label=self._label(ctx, c, dims, full=True),
                    depth=self._depth(c, totals),
                    group=keys[c],
                    parent=None,
                )
                for c in combos
            ],
            rows=rows,
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
        categories: Sequence[str] = (),
    ) -> tuple[KpiConfig, list[str], list[Observation], Provenance]:
        """Observações para exportação (formato longo)."""
        kpi = self.kpi(ctx, kpi_id)
        dims = self._dims(kpi, dimensions, level)
        sel = self._selection(ctx, kpi, categories)
        grain = self._grain(ctx, kpi, grain)
        for p in periods:
            self._period(ctx, kpi, p, grain, level)
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
            selected=sel,
            for_export=True,
        )
        return kpi, dims, obs, prov


def _period_label(period: str) -> str:
    """Rótulo curto do período, como no portal: "jan/2025", "T2 2025", "S1 2025", "2025"."""
    return _price_base(period)


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


def _json(model: NavigationOut | KpiOut | PortalIndexOut) -> bytes:
    """Mesmo JSON que o FastAPI produz para o ``response_model`` (compacto, UTF-8)."""
    return json.dumps(
        model.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
