"""Consultas do bloco de contas públicas sobre o release do escopo ``contas`` (ADR-0037).

Regras:

* **SQL só de modelos fixos.** Dimensões, agrupamentos e níveis vêm de listas fechadas;
  meses e anos entram no texto só depois de conferidos contra a ``agg_contas_period_status``
  do release; os valores do usuário (códigos, textos, chaves) vão como parâmetros.
* **Nada pesado na requisição** (§5.3.8): mapa, composição e série leem o agregado; o
  ranking lê o ranking pronto; a tabela lê o fato particionado por ano e devolve só a
  página pedida (10 linhas, até 100 páginas).
* **Só o nome na tela** (ADR-0034, decisão 6): nenhuma resposta traz CNPJ, CPF mascarado
  ou código do favorecido.
"""

from __future__ import annotations

import math
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from odb_api.contas_schemas import (
    CompositionRowOut,
    ContasCompositionOut,
    ContasDimensionOut,
    ContasExecutionOut,
    ContasMapOut,
    ContasMetaOut,
    ContasProvenance,
    ContasRankingOut,
    ContasSearchOut,
    ContasSeriesOut,
    ContasTableOut,
    ContasTableRowOut,
    ExecutionRowOut,
    Lens,
    LensOut,
    LensPointOut,
    LensTotalOut,
    MapRowOut,
    OrganTotalOut,
    PeriodStatusOut,
    RankingRowOut,
    RecipientProfileOut,
    RecipientRefOut,
    SearchHitOut,
    SeriesLineOut,
    SeriesPointOut,
)
from odb_api.gold import GoldGateway, NotFoundError
from odb_api.release import ReleaseContext, ReleaseResolver
from odb_api.schemas import TableVersionOut
from odb_modeling.contas import CLASS_LABELS, MISSING_CODE, NOT_RANKED
from odb_processing.datasus import UF_CODES
from odb_semantics import SemanticError
from odb_semantics.periods import PeriodError, months_of

PAGE_SIZE = 10
_LENSES_AB: tuple[Lens, Lens] = ("A", "B")
MAX_PAGES = 100  # ADR-0034, decisão 3: além disso, filtro ou exportação.
TOP_CATEGORIES = 10
MAX_FILTERS = 10
MAX_CATEGORIES = 50
_MONTH = re.compile(r"^\d{4}M\d{2}$")
LEVELS = ("brasil", "regiao", "uf", "municipio")

LENS_LABELS = {
    "A": "Recursos transferidos",
    "B": "Recebimento por favorecido",
    "C": "Execução da despesa",
}
LENS_DESCRIPTIONS = {
    "A": "Pagamentos da União a estados, municípios, fundos e entidades, pelo município do "
    "ente ou da entidade que recebeu.",
    "B": "Tudo o que cada favorecido recebeu da União, pelo município da sede cadastral.",
    "C": "Empenhado, liquidado, pago e restos a pagar da União, sem território.",
}
LENS_NOTES = {
    "A": [
        "O valor é o que a União pagou ao ente: como ele gasta esse dinheiro não está nas "
        "bases federais.",
        "O FPM que falta na fonte (as parcelas adicionais de julho, setembro e dezembro "
        "desde 2025 e os meses sem FPM) vem da distribuição por município do Tesouro "
        "Nacional (Fonte: Tesouro Nacional, Tesouro Transparente; licença ODbL).",
    ],
    "B": [
        "O território é a sede do favorecido, não o local do serviço: uma empresa de SP que "
        "faz obra na PB aparece em SP.",
        "Lançamentos agregados, fluxos dentro da União, bancos pagadores e sigilosos entram "
        "nos totais, mas não nos rankings.",
    ],
    "C": ["As fases nunca se somam: empenhado, liquidado e pago são etapas do mesmo gasto."],
}
NOTES = [
    "As lentes não se somam: cada uma responde uma pergunta diferente.",
    "Valores nominais, sem correção pela inflação.",
]
HOMONYM_NOTE = (
    "O CPF mascarado não distingue pessoas: pode haver homônimos. Confira a página oficial "
    "no Portal da Transparência."
)

# Dimensão → rótulo (a ordem é a da interface).
DIMENSION_LABELS = {
    "transfer_type": "Tipo de transferência",
    "function": "Função",
    "subfunction": "Subfunção",
    "program": "Programa",
    "action": "Ação",
    "superior_organ": "Órgão superior",
    "organ": "Órgão",
    "management_unit": "Unidade gestora",
    "expense_group": "Grupo de despesa",
    "application_modality": "Modalidade de aplicação",
    "expense_element": "Elemento de despesa",
    "recipient_class": "Classe do favorecido",
    "cnae_section": "Atividade econômica",
    "amendment_author": "Autor de emenda",
}
MAP_DIMENSIONS = {
    "A": (
        "transfer_type", "function", "subfunction", "program", "action", "superior_organ",
        "organ", "expense_group", "application_modality", "expense_element", "recipient_class",
    ),
    "B": ("superior_organ", "organ", "management_unit", "recipient_class", "cnae_section"),
}  # fmt: skip


@dataclass(frozen=True, slots=True)
class _Column:
    """Código e rótulo de um agrupamento sobre o fato, e as dimensões que ele exige."""

    code: str
    label: str
    joins: tuple[str, ...] = ()


# Agrupamentos e filtros da tabela, por lente (aliases: f fato, a ação, u UG, n natureza,
# r favorecido).
_TABLE_COLUMNS: Mapping[str, Mapping[str, _Column]] = {
    "A": {
        "transfer_type": _Column("f.transfer_type", "f.transfer_type"),
        "function": _Column("a.function_code", "a.function_name", ("a",)),
        "subfunction": _Column("a.subfunction_code", "a.subfunction_name", ("a",)),
        "program": _Column("a.program_code", "a.program_name", ("a",)),
        "action": _Column("a.action_code", "a.action_name", ("a",)),
        "superior_organ": _Column("u.superior_organ_code", "u.superior_organ_name", ("u",)),
        "organ": _Column("u.organ_code", "u.organ_name", ("u",)),
        "expense_group": _Column("n.expense_group_code", "n.expense_group_name", ("n",)),
        "application_modality": _Column(
            "n.application_modality_code", "n.application_modality_name", ("n",)
        ),
        "expense_element": _Column("n.expense_element_code", "n.expense_element_name", ("n",)),
        "recipient_class": _Column("f.recipient_class", "f.recipient_class"),
    },
    "B": {
        "superior_organ": _Column("u.superior_organ_code", "u.superior_organ_name", ("u",)),
        "organ": _Column("u.organ_code", "u.organ_name", ("u",)),
        "management_unit": _Column("u.management_unit_code", "u.management_unit_name", ("u",)),
        "recipient_class": _Column("f.recipient_class", "f.recipient_class"),
        "cnae_section": _Column("r.cnae_section_code", "r.cnae_section_description", ("r",)),
    },
}
_EXECUTION_COLUMNS: Mapping[str, _Column] = {
    "function": _Column("a.function_code", "a.function_name", ("a",)),
    "subfunction": _Column("a.subfunction_code", "a.subfunction_name", ("a",)),
    "program": _Column("a.program_code", "a.program_name", ("a",)),
    "action": _Column("a.action_code", "a.action_name", ("a",)),
    "superior_organ": _Column("u.superior_organ_code", "u.superior_organ_name", ("u",)),
    "organ": _Column("u.organ_code", "u.organ_name", ("u",)),
    "expense_group": _Column("n.expense_group_code", "n.expense_group_name", ("n",)),
    "application_modality": _Column(
        "n.application_modality_code", "n.application_modality_name", ("n",)
    ),
    "expense_element": _Column("n.expense_element_code", "n.expense_element_name", ("n",)),
    "amendment_author": _Column("e.amendment_author_code", "e.amendment_author_name", ("e",)),
}
_JOINS = {
    "a": ("a", "dim_budget_action", "a.action_key = f.action_key"),
    "u": ("u", "dim_management_unit", "u.ug_key = f.ug_key"),
    "n": ("n", "dim_expense_nature", "n.nature_key = f.nature_key"),
    "r": ("r", "dim_recipient", "r.recipient_key = f.recipient_key"),
    "e": ("e", "dim_amendment_author", "e.author_key = f.author_key"),
}
FACTS = {
    "A": "fact_federal_transfer",
    "B": "fact_federal_payment_recipient",
    "C": "fact_federal_budget_execution",
}
_PHASES = (
    "committed",
    "liquidated",
    "paid",
    "payables_registered",
    "payables_cancelled",
    "payables_paid",
)
_CHILD_LEVEL = {"brasil": "regiao", "regiao": "uf", "uf": "municipio"}
_OUTSIDE = {
    "regiao": "Sem UF (exterior, sem informação ou múltiplo)",
    "uf": "Sem UF (exterior, sem informação ou múltiplo)",
    "municipio": "Sem município (favorecidos estaduais)",
}


def _level_of(geography_key: str) -> str:
    """Nível de uma chave territorial (``uf:25`` → ``uf``), só entre os do bloco."""
    level = geography_key.partition(":")[0]
    if level not in LEVELS:
        msg = f"nível territorial sem contas públicas: {geography_key}"
        raise SemanticError(msg)
    return level


def _partition(alias: str, lens: str, level: str) -> str:
    """Filtro das partições (lente e nível) com literais conferidos: o DuckDB poda."""
    if lens not in ("A", "B") or level not in LEVELS:
        msg = f"lente {lens!r} ou nível {level!r} inválido"
        raise SemanticError(msg)
    return f"{alias}.lens = '{lens}' AND {alias}.level_id = '{level}'"


def _float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _share(value: float, total: float) -> float | None:
    return value / total if total else None


class ContasService:
    """Consultas do bloco 2, sempre no release resolvido do escopo ``contas``."""

    def __init__(self, gold: GoldGateway, resolver: ReleaseResolver) -> None:
        """Recebe o motor da Gold e o resolvedor do release das contas."""
        self._gold = gold
        self.resolver = resolver
        self._status: dict[str, dict[str, list[PeriodStatusOut]]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------- utilitários

    def _rows(
        self,
        ctx: ReleaseContext,
        sql: str,
        tables: Mapping[str, str],
        params: Mapping[str, Any] | None = None,
        max_rows: int | None = None,
    ) -> list[dict[str, Any]]:
        result = self._gold.execute(ctx, sql, tables, params, max_rows=max_rows)
        return [dict(zip(result.columns, r, strict=True)) for r in result.rows]

    def statuses(self, ctx: ReleaseContext) -> dict[str, list[PeriodStatusOut]]:
        """Situação de cada mês por lente, guardada por release (tabela de 105 linhas)."""
        with self._lock:
            found = self._status.get(ctx.release_id)
        if found is not None:
            return found
        rows = self._rows(
            ctx,
            "SELECT lens, period, status, note, shortfall_share, missing_actions "
            "FROM {{s}} ORDER BY lens, period",
            {"s": "agg_contas_period_status"},
        )
        out: dict[str, list[PeriodStatusOut]] = {}
        for r in rows:
            out.setdefault(r["lens"], []).append(
                PeriodStatusOut(
                    period=r["period"],
                    status=r["status"],
                    note=r["note"],
                    shortfall_share=r["shortfall_share"],
                    missing_actions=list(r["missing_actions"] or []),
                )
            )
        with self._lock:
            self._status = {ctx.release_id: out}  # só o release vigente
        return out

    def months(self, ctx: ReleaseContext, lens: str, periods: Sequence[str]) -> list[str]:
        """Meses publicados que compõem os períodos pedidos (padrão: o último ano).

        Aceita mês, trimestre, semestre e ano (ADR-0013). Um período sem nenhum mês
        publicado é recusado.
        """
        available = [s.period for s in self.statuses(ctx).get(lens, [])]
        if not available:
            msg = f"lente {lens} sem meses publicados neste release"
            raise SemanticError(msg)
        if not periods:
            year = available[-1][:4]
            return [m for m in available if m.startswith(year)]
        wanted: list[str] = []
        for code in periods:
            try:
                wanted.extend(months_of(code))
            except PeriodError as exc:
                raise SemanticError(str(exc)) from exc
        chosen = sorted(set(wanted) & set(available))
        if not chosen:
            msg = f"nenhum mês publicado em {list(periods)} (de {available[0]} a {available[-1]})"
            raise SemanticError(msg)
        return chosen

    def _provenance(
        self, ctx: ReleaseContext, lens: str, months: Sequence[str], tables: Sequence[str]
    ) -> ContasProvenance:
        notes = [
            s
            for s in self.statuses(ctx).get(lens, [])
            if s.period in months and s.status != "fechado"
        ]
        return ContasProvenance(
            release_id=ctx.release_id,
            tables=[
                TableVersionOut(table_id=t, delta_version=ctx.release.tables[t].delta_version)
                for t in sorted(set(tables))
            ],
            periods=list(months),
            partial=bool(notes),
            period_notes=notes,
        )

    @staticmethod
    def _in_list(months: Sequence[str]) -> str:
        """Lista SQL de meses já conferidos contra o release (formato ``AAAAMmm``)."""
        assert all(_MONTH.match(m) for m in months)  # noqa: S101 - validado em months()
        return ", ".join(f"'{m}'" for m in months)

    @staticmethod
    def _years(months: Sequence[str]) -> str:
        return ", ".join(sorted({str(int(m[:4])) for m in months}))

    def _territory(self, ctx: ReleaseContext, geography_key: str) -> dict[str, Any]:
        row = self._gold.geography(ctx, geography_key)
        if row.get("level_id") not in LEVELS:
            msg = f"nível territorial sem contas públicas: {geography_key}"
            raise SemanticError(msg)
        return row

    @staticmethod
    def _check_dimension(lens: str, dimension: str | None) -> None:
        if dimension is not None and dimension not in MAP_DIMENSIONS[lens]:
            msg = f"dimensão {dimension!r} indisponível na lente {lens}: {MAP_DIMENSIONS[lens]}"
            raise SemanticError(msg)

    @staticmethod
    def _recipient(row: Mapping[str, Any]) -> RecipientRefOut:
        klass = str(row["recipient_class"])
        return RecipientRefOut(
            recipient_id=row["recipient_id"],
            name=row["recipient_name"],
            seat_municipality=row.get("seat_municipality_name"),
            seat_uf=row.get("seat_uf"),
            recipient_class=klass,
            class_label=CLASS_LABELS.get(klass, klass),
            is_natural_person=bool(row["is_natural_person"]),
        )

    # ------------------------------------------------------------- meta

    def meta(self, ctx: ReleaseContext) -> ContasMetaOut:
        """Lentes, dimensões, meses e situação de cada mês."""
        statuses = self.statuses(ctx)
        lenses = []
        for lens in ("A", "B", "C"):
            items = statuses.get(lens, [])
            dims = MAP_DIMENSIONS.get(lens, tuple(_EXECUTION_COLUMNS))
            group = (
                ("territory", *_TABLE_COLUMNS[lens], "recipient")
                if lens in _TABLE_COLUMNS
                else tuple(_EXECUTION_COLUMNS)
            )
            lenses.append(
                LensOut(
                    lens=lens,
                    label=LENS_LABELS[lens],
                    description=LENS_DESCRIPTIONS[lens],
                    notes=LENS_NOTES[lens],
                    dimensions=[ContasDimensionOut(id=d, label=DIMENSION_LABELS[d]) for d in dims],
                    group_by=[
                        ContasDimensionOut(
                            id=g, label=DIMENSION_LABELS.get(g, _GROUP_LABELS.get(g, g))
                        )
                        for g in group
                    ],
                    periods=[s.period for s in items],
                    latest_period=items[-1].period if items else None,
                    statuses=items,
                )
            )
        return ContasMetaOut(
            release_id=ctx.release_id,
            lenses=lenses,
            recipient_classes=dict(CLASS_LABELS),
            notes=NOTES,
        )

    # ------------------------------------------------------------- mapa, composição, série

    def map(
        self,
        ctx: ReleaseContext,
        *,
        lens: str,
        level: str,
        within: str | None,
        periods: Sequence[str],
        dimension: str | None,
        categories: Sequence[str],
    ) -> ContasMapOut:
        """Total por território no nível pedido (opcionalmente dentro de um território)."""
        if level not in LEVELS:
            msg = f"nível {level!r} fora de {LEVELS}"
            raise SemanticError(msg)
        self._check_dimension(lens, dimension)
        if categories and dimension is None:
            msg = "categorias exigem uma dimensão (detalhar por)"
            raise SemanticError(msg)
        months = self.months(ctx, lens, periods)
        params: dict[str, Any] = {"dim": dimension or "total"}
        where = [
            _partition("a", lens, level),
            f"a.year IN ({self._years(months)})",
            f"a.period IN ({self._in_list(months)})",
            "a.dimension_id = $dim",
        ]
        if categories:
            where.append("list_contains(CAST($cats AS VARCHAR[]), a.category_code)")
            params["cats"] = list(categories)
        if within:
            parent = self._territory(ctx, within)
            if parent["level_id"] not in ("brasil",):
                where.append(
                    "(g.uf_code = $within_code OR g.region_code = $within_code "
                    "OR g.geography_key = $within)"
                    if parent["level_id"] != "municipio"
                    else "g.geography_key = $within"
                )
                params["within_code"] = parent["territory_code"]
                params["within"] = within
        rows = self._rows(
            ctx,
            "SELECT a.geography_key, g.name, sum(a.value) AS value "
            "FROM {{agg}} a JOIN {{geo}} g ON g.geography_key = a.geography_key "
            f"WHERE {' AND '.join(where)} GROUP BY 1, 2 ORDER BY value DESC",
            {"agg": "agg_contas_territory", "geo": "dim_geography"},
            params,
            max_rows=6000,
        )
        out = [
            MapRowOut(geography_key=r["geography_key"], name=r["name"], value=_float(r["value"]))
            for r in rows
        ]
        return ContasMapOut(
            lens=lens,  # type: ignore[arg-type]
            level=level,
            within=within,
            dimension=dimension,
            categories=list(categories),
            total=sum(r.value for r in out),
            rows=out,
            provenance=self._provenance(
                ctx, lens, months, ["agg_contas_territory", "dim_geography"]
            ),
        )

    def composition(
        self,
        ctx: ReleaseContext,
        *,
        lens: str,
        geography_key: str,
        periods: Sequence[str],
        dimension: str,
        limit: int = TOP_CATEGORIES,
    ) -> ContasCompositionOut:
        """As ``limit`` maiores categorias do território e "demais" (tooltip, ADR-0034)."""
        self._check_dimension(lens, dimension)
        self._territory(ctx, geography_key)
        months = self.months(ctx, lens, periods)
        rows = self._category_totals(ctx, lens, geography_key, months, dimension)
        total = sum(_float(r["value"]) for r in rows)
        top = rows[:limit]
        out = [
            CompositionRowOut(
                category_code=r["category_code"],
                label=r["label"],
                value=_float(r["value"]),
                share=_share(_float(r["value"]), total),
            )
            for r in top
        ]
        rest = rows[limit:]
        if rest:
            value = sum(_float(r["value"]) for r in rest)
            out.append(
                CompositionRowOut(
                    category_code="demais",
                    label=f"Demais ({len(rest)})",
                    value=value,
                    share=_share(value, total),
                )
            )
        return ContasCompositionOut(
            lens=lens,  # type: ignore[arg-type]
            geography_key=geography_key,
            dimension=dimension,
            total=total,
            rows=out,
            provenance=self._provenance(ctx, lens, months, ["agg_contas_territory"]),
        )

    def _category_totals(
        self,
        ctx: ReleaseContext,
        lens: str,
        geography_key: str,
        months: Sequence[str],
        dimension: str,
    ) -> list[dict[str, Any]]:
        return self._rows(
            ctx,
            "SELECT category_code, max(category_label) AS label, sum(value) AS value "
            f"FROM {{{{agg}}}} a WHERE {_partition('a', lens, _level_of(geography_key))} "
            "AND a.geography_key = $geo AND a.dimension_id = $dim "
            f"AND year IN ({self._years(months)}) AND period IN ({self._in_list(months)}) "
            "GROUP BY 1 ORDER BY value DESC, category_code",
            {"agg": "agg_contas_territory"},
            {"geo": geography_key, "dim": dimension},
        )

    def series(
        self,
        ctx: ReleaseContext,
        *,
        lens: str,
        geography_key: str,
        periods: Sequence[str],
        grain: str,
        dimension: str | None,
        categories: Sequence[str],
    ) -> ContasSeriesOut:
        """Série mensal ou anual do total, ou das maiores categorias + "demais"."""
        self._check_dimension(lens, dimension)
        self._territory(ctx, geography_key)
        if periods:
            months = self.months(ctx, lens, periods)
        else:  # série: todos os meses publicados
            months = [s.period for s in self.statuses(ctx).get(lens, [])]
        bucket = "a.period" if grain == "mes" else "CAST(a.year AS VARCHAR)"
        params: dict[str, Any] = {"geo": geography_key, "dim": dimension or "total"}
        chosen: list[str] = []
        labels: dict[str, str] = {}
        if dimension is not None:
            totals = self._category_totals(ctx, lens, geography_key, months, dimension)
            labels = {r["category_code"]: r["label"] for r in totals}
            chosen = list(categories) or [r["category_code"] for r in totals[:TOP_CATEGORIES]]
        rows = self._rows(
            ctx,
            f"SELECT {bucket} AS bucket, a.category_code, sum(a.value) AS value "
            f"FROM {{{{agg}}}} a WHERE {_partition('a', lens, _level_of(geography_key))} "
            "AND a.geography_key = $geo "
            f"AND a.dimension_id = $dim AND a.year IN ({self._years(months)}) "
            f"AND a.period IN ({self._in_list(months)}) GROUP BY 1, 2 ORDER BY 1",
            {"agg": "agg_contas_territory"},
            params,
        )
        lines: dict[str, dict[str, float]] = {}
        for r in rows:
            code = r["category_code"]
            if dimension is not None and code not in chosen:
                code = "demais"
            line = lines.setdefault(code, {})
            line[r["bucket"]] = line.get(r["bucket"], 0.0) + _float(r["value"])
        order = ["total"] if dimension is None else [*chosen, "demais"]
        out = [
            SeriesLineOut(
                category_code=code,
                label="Total" if code == "total" else labels.get(code, "Demais"),
                points=[SeriesPointOut(period=p, value=v) for p, v in sorted(lines[code].items())],
            )
            for code in order
            if code in lines
        ]
        return ContasSeriesOut(
            lens=lens,  # type: ignore[arg-type]
            geography_key=geography_key,
            grain=grain,  # type: ignore[arg-type]
            dimension=dimension,
            lines=out,
            provenance=self._provenance(ctx, lens, months, ["agg_contas_territory"]),
        )

    # ------------------------------------------------------------- ranking e tabela

    def ranking(
        self, ctx: ReleaseContext, *, lens: str, geography_key: str, year: int | None, page: int
    ) -> ContasRankingOut:
        """Página do ranking pronto (os 1.000 maiores do território no ano)."""
        self._territory(ctx, geography_key)
        available = [s.period for s in self.statuses(ctx).get(lens, [])]
        years = sorted({int(p[:4]) for p in available})
        if not years:
            msg = f"lente {lens} sem meses publicados"
            raise SemanticError(msg)
        year = year or years[-1]
        if year not in years:
            msg = f"ano {year} fora dos publicados: {years}"
            raise SemanticError(msg)
        rows = self._rows(
            ctx,
            "SELECT k.rank, k.value, k.recipients_in_territory, r.recipient_id, r.recipient_name, "
            "r.seat_municipality_name, r.seat_uf, r.recipient_class, r.is_natural_person "
            "FROM {{rank}} k JOIN {{rec}} r ON r.recipient_key = k.recipient_key "
            f"WHERE {_partition('k', lens, _level_of(geography_key))} "
            "AND k.geography_key = $geo AND k.year = $year "
            "AND k.rank > $start AND k.rank <= $end ORDER BY k.rank",
            {"rank": "agg_recipient_rank", "rec": "dim_recipient"},
            {
                "geo": geography_key,
                "year": year,
                "start": (page - 1) * PAGE_SIZE,
                "end": page * PAGE_SIZE,
            },
        )
        total = (
            int(rows[0]["recipients_in_territory"])
            if rows
            else self._ranked_total(ctx, lens, geography_key, year)
        )
        months = [m for m in available if m.startswith(str(year))]
        out = [
            RankingRowOut(
                rank=int(r["rank"]), recipient=self._recipient(r), value=_float(r["value"])
            )
            for r in rows
        ]
        return ContasRankingOut(
            lens=lens,  # type: ignore[arg-type]
            geography_key=geography_key,
            year=year,
            page=page,
            page_size=PAGE_SIZE,
            pages=min(MAX_PAGES, math.ceil(total / PAGE_SIZE)),
            total_recipients=total,
            rows=out,
            notes=[HOMONYM_NOTE] if any(r.recipient.is_natural_person for r in out) else [],
            provenance=self._provenance(ctx, lens, months, ["agg_recipient_rank", "dim_recipient"]),
        )

    def _ranked_total(self, ctx: ReleaseContext, lens: str, geography_key: str, year: int) -> int:
        rows = self._rows(
            ctx,
            "SELECT max(recipients_in_territory) AS n FROM {{rank}} k "
            f"WHERE {_partition('k', lens, _level_of(geography_key))} "
            "AND k.geography_key = $geo AND k.year = $year",
            {"rank": "agg_recipient_rank"},
            {"geo": geography_key, "year": year},
        )
        return int(rows[0]["n"] or 0) if rows else 0

    @staticmethod
    def _territory_filter(level: str, code: str) -> str:
        """Filtro de território com literais validados: poda as partições por UF."""
        if not re.fullmatch(r"\d{1,7}", code):
            msg = f"código territorial inválido: {code!r}"
            raise SemanticError(msg)
        if level == "brasil":
            return "TRUE"
        if level == "regiao":
            ufs = ", ".join(f"'{uf}'" for uf in sorted(UF_CODES.values()) if uf[0] == code)
            return f"f.uf_code IN ({ufs})"
        if level == "uf":
            return f"f.uf_code = '{code}'"
        return f"f.uf_code = '{code[:2]}' AND f.municipality_id = '{code}'"

    def table(
        self,
        ctx: ReleaseContext,
        *,
        lens: str,
        geography_key: str,
        periods: Sequence[str],
        group_by: str,
        filters: Sequence[str],
        sort: str,
        page: int,
        include_intermediaries: bool,
    ) -> ContasTableOut:
        """Tabela paginada sobre o fato: agrupa e devolve só a página pedida."""
        territory = self._territory(ctx, geography_key)
        level = str(territory["level_id"])
        months = self.months(ctx, lens, periods)
        columns = _TABLE_COLUMNS[lens]
        if group_by not in (*columns, "territory", "recipient"):
            msg = f"agrupamento {group_by!r} indisponível na lente {lens}"
            raise SemanticError(msg)
        if group_by == "territory" and level not in _CHILD_LEVEL:
            msg = "município não tem nível abaixo; agrupe por outra dimensão"
            raise SemanticError(msg)
        if len(filters) > MAX_FILTERS:
            msg = f"no máximo {MAX_FILTERS} filtros"
            raise SemanticError(msg)
        q = _table_sql(
            lens=lens,
            level=level,
            where=[
                f"f.year IN ({self._years(months)})",
                f"f.period IN ({self._in_list(months)})",
                self._territory_filter(level, str(territory["territory_code"])),
            ],
            group_by=group_by,
            filters=filters,
            sort=sort,
            include_intermediaries=include_intermediaries,
        )
        named, tables, params, notes, order = q.named, q.tables, q.params, q.notes, q.order
        rows = self._rows(
            ctx,
            f"WITH g AS ({named}) SELECT key, label, value, "
            "count(*) OVER () AS n, sum(value) OVER () AS total "
            f"FROM g ORDER BY {order} LIMIT {PAGE_SIZE} OFFSET $offset",
            tables,
            {**params, "offset": (page - 1) * PAGE_SIZE},
        )
        if not rows:
            count = self._rows(
                ctx, f"SELECT count(*) AS n, sum(value) AS total FROM ({named})", tables, params
            )[0]
        else:
            count = {"n": rows[0]["n"], "total": rows[0]["total"]}
        total_rows = int(count["n"] or 0)
        value_total = _float(count["total"])
        outside = _OUTSIDE[_CHILD_LEVEL[level]] if group_by == "territory" else ""
        out = self._table_rows(ctx, group_by, rows, value_total, outside)
        if any(r.recipient and r.recipient.is_natural_person for r in out):
            notes.append(HOMONYM_NOTE)
        used = [*tables.values()]
        if group_by in ("recipient", "territory"):
            used.append("dim_recipient" if group_by == "recipient" else "dim_geography")
        return ContasTableOut(
            lens=lens,  # type: ignore[arg-type]
            geography_key=geography_key,
            group_by=group_by,
            filters=list(filters),
            sort=sort,  # type: ignore[arg-type]
            page=page,
            page_size=PAGE_SIZE,
            pages=min(MAX_PAGES, math.ceil(total_rows / PAGE_SIZE)),
            rows_total=total_rows,
            value_total=value_total,
            page_value=sum(r.value for r in out),
            rows=out,
            notes=notes,
            provenance=self._provenance(ctx, lens, months, used),
        )

    def _table_rows(
        self,
        ctx: ReleaseContext,
        group_by: str,
        rows: Sequence[Mapping[str, Any]],
        total: float,
        outside: str,
    ) -> list[ContasTableRowOut]:
        if group_by == "recipient":
            keys = [int(r["key"]) for r in rows]
            found = (
                {
                    int(x["recipient_key"]): x
                    for x in self._rows(
                        ctx,
                        "SELECT recipient_key, recipient_id, recipient_name, "
                        "seat_municipality_name, seat_uf, recipient_class, is_natural_person "
                        "FROM {{rec}} "
                        "WHERE list_contains(CAST($keys AS BIGINT[]), recipient_key)",
                        {"rec": "dim_recipient"},
                        {"keys": keys},
                    )
                }
                if keys
                else {}
            )
            out = []
            for r in rows:
                ref = self._recipient(found[int(r["key"])])
                out.append(
                    ContasTableRowOut(
                        key=ref.recipient_id,
                        label=ref.name or "(sem nome na fonte)",
                        value=_float(r["value"]),
                        share=_share(_float(r["value"]), total),
                        recipient=ref,
                    )
                )
            return out
        if group_by == "territory":
            geo_keys = [str(r["key"]) for r in rows]
            names = (
                {
                    x["geography_key"]: x["name"]
                    for x in self._rows(
                        ctx,
                        "SELECT geography_key, name FROM {{geo}} "
                        "WHERE list_contains(CAST($keys AS VARCHAR[]), geography_key)",
                        {"geo": "dim_geography"},
                        {"keys": geo_keys},
                    )
                }
                if geo_keys
                else {}
            )
            return [
                ContasTableRowOut(
                    key=str(r["key"]),
                    label=names.get(str(r["key"]), outside),
                    value=_float(r["value"]),
                    share=_share(_float(r["value"]), total),
                )
                for r in rows
            ]
        labels = CLASS_LABELS if group_by == "recipient_class" else {}
        return [
            ContasTableRowOut(
                key=str(r["key"]),
                label=labels.get(str(r["key"]), r["label"] or "Não se aplica ou sem informação"),
                value=_float(r["value"]),
                share=_share(_float(r["value"]), total),
            )
            for r in rows
        ]

    # ------------------------------------------------------------- favorecido e busca

    def recipient(
        self, ctx: ReleaseContext, recipient_id: str, periods: Sequence[str]
    ) -> RecipientProfileOut:
        """Ficha do favorecido nas lentes A e B."""
        found = self._rows(
            ctx,
            "SELECT * FROM {{rec}} WHERE recipient_id = $id",
            {"rec": "dim_recipient"},
            {"id": recipient_id},
        )
        if not found:
            msg = f"favorecido {recipient_id} inexistente no release"
            raise NotFoundError(msg)
        row = found[0]
        key = int(row["recipient_key"])
        totals: list[LensTotalOut] = []
        organs: list[OrganTotalOut] = []
        series: list[LensPointOut] = []
        months_all: list[str] = []
        by_ug: dict[tuple[str, int], float] = {}
        for lens in ("A", "B"):
            months = self.months(ctx, lens, periods)
            months_all.extend(months)
            # Uma leitura do fato por lente: mês x UG; série, anos e órgãos saem daqui.
            rows = self._rows(
                ctx,
                "SELECT f.period, f.ug_key, sum(f.value) AS value FROM {{f}} f "
                f"WHERE f.recipient_key = $key AND f.year IN ({self._years(months)}) "
                f"AND f.period IN ({self._in_list(months)}) GROUP BY 1, 2",
                {"f": FACTS[lens]},
                {"key": key},
            )
            by_period: dict[str, float] = {}
            for r in rows:
                value = _float(r["value"])
                by_period[r["period"]] = by_period.get(r["period"], 0.0) + value
                ug = (lens, int(r["ug_key"]))
                by_ug[ug] = by_ug.get(ug, 0.0) + value
            series.extend(
                LensPointOut(lens=lens, period=p, value=v) for p, v in sorted(by_period.items())
            )
            by_year: dict[int, float] = {}
            for period, value in by_period.items():
                by_year[int(period[:4])] = by_year.get(int(period[:4]), 0.0) + value
            totals.extend(
                LensTotalOut(lens=lens, year=y, value=v) for y, v in sorted(by_year.items())
            )
        organs.extend(self._organs(ctx, by_ug))
        ref = self._recipient(row)
        notes = [HOMONYM_NOTE] if ref.is_natural_person else []
        return RecipientProfileOut(
            recipient=ref,
            legal_nature=row.get("legal_nature_description"),
            economic_activity=row.get("cnae_description"),
            economic_section=row.get("cnae_section_description"),
            totals=totals,
            organs=organs,
            series=series,
            notes=notes,
            provenance=self._provenance(
                ctx,
                "B",
                sorted(set(months_all)),
                ["dim_recipient", "dim_management_unit", FACTS["A"], FACTS["B"]],
            ),
        )

    def _organs(
        self, ctx: ReleaseContext, by_ug: Mapping[tuple[str, int], float]
    ) -> list[OrganTotalOut]:
        """Os 10 maiores órgãos de cada lente, a partir dos totais por UG."""
        keys = sorted({k for _, k in by_ug})
        if not keys:
            return []
        organ_of = {
            int(r["ug_key"]): r["organ_name"]
            for r in self._rows(
                ctx,
                "SELECT ug_key, organ_name FROM {{u}} "
                "WHERE list_contains(CAST($keys AS INTEGER[]), ug_key)",
                {"u": "dim_management_unit"},
                {"keys": keys},
            )
        }
        totals: dict[tuple[str, str | None], float] = {}
        for (lens, ug), value in by_ug.items():
            name = organ_of.get(ug)
            totals[(lens, name)] = totals.get((lens, name), 0.0) + value
        out: list[OrganTotalOut] = []
        for lens in _LENSES_AB:
            ranked = sorted(
                ((n, v) for (le, n), v in totals.items() if le == lens), key=lambda x: -x[1]
            )
            out.extend(OrganTotalOut(lens=lens, organ=n, value=v) for n, v in ranked[:10])
        return out

    def search(self, ctx: ReleaseContext, q: str, limit: int) -> ContasSearchOut:
        """Favorecidos PJ, órgãos, programas e ações pelo nome (sem acento e caixa).

        Pessoas físicas ficam fora da busca (plano, seção 9): aparecem só nos totais,
        tabelas e rankings dos territórios.
        """
        text = q.strip()
        if len(text) < 3:  # noqa: PLR2004
            msg = "busca com pelo menos 3 letras"
            raise SemanticError(msg)
        like = {"q": f"%{text}%"}
        match = "strip_accents(lower({col})) LIKE strip_accents(lower($q))"
        hits: list[SearchHitOut] = []
        for r in self._rows(
            ctx,
            "SELECT recipient_id, recipient_name, seat_municipality_name, seat_uf FROM {{rec}} "
            f"WHERE NOT is_natural_person AND {match.format(col='recipient_name')} "
            f"ORDER BY length(recipient_name), recipient_name LIMIT {int(limit)}",
            {"rec": "dim_recipient"},
            like,
        ):
            seat = "/".join(x for x in (r["seat_municipality_name"], r["seat_uf"]) if x)
            hits.append(
                SearchHitOut(
                    kind="favorecido",
                    id=r["recipient_id"],
                    label=r["recipient_name"],
                    detail=seat or None,
                )
            )
        for r in self._rows(
            ctx,
            "SELECT organ_code, max(organ_name) AS name FROM {{u}} "
            f"WHERE {match.format(col='organ_name')} GROUP BY 1 ORDER BY 2 LIMIT 5",
            {"u": "dim_management_unit"},
            like,
        ):
            hits.append(SearchHitOut(kind="orgao", id=f"organ:{r['organ_code']}", label=r["name"]))
        for kind, code, name in (("programa", "program_code", "program_name"),
                                 ("acao", "action_code", "action_name")):  # fmt: skip
            dim = "program" if kind == "programa" else "action"
            for r in self._rows(
                ctx,
                f"SELECT {code} AS code, arg_max({name}, fiscal_year) AS name, "
                "max(fiscal_year) AS year FROM {{a}} "
                f"WHERE {match.format(col=name)} GROUP BY 1 ORDER BY 2 LIMIT 5",
                {"a": "dim_budget_action"},
                like,
            ):
                hits.append(
                    SearchHitOut(
                        kind=kind,  # type: ignore[arg-type]
                        id=f"{dim}:{r['code']}",
                        label=r["name"],
                        detail=f"exercício {r['year']}",
                    )
                )
        return ContasSearchOut(q=text, hits=hits, release_id=ctx.release_id)

    # ------------------------------------------------------------- execução (lente C)

    def execution(
        self,
        ctx: ReleaseContext,
        *,
        periods: Sequence[str],
        dimension: str,
        filters: Sequence[str],
        page: int,
    ) -> ContasExecutionOut:
        """Fases da despesa por categoria, paginadas, ordenadas pelo pago."""
        if dimension not in _EXECUTION_COLUMNS:
            msg = f"dimensão {dimension!r} indisponível na lente C: {list(_EXECUTION_COLUMNS)}"
            raise SemanticError(msg)
        months = self.months(ctx, "C", periods)
        column = _EXECUTION_COLUMNS[dimension]
        joins = set(column.joins)
        params: dict[str, Any] = {"offset": (page - 1) * PAGE_SIZE}
        where = [f"f.year IN ({self._years(months)})", f"f.period IN ({self._in_list(months)})"]
        for i, item in enumerate(filters[:MAX_FILTERS]):
            dim, _, code = item.partition(":")
            col = _EXECUTION_COLUMNS.get(dim)
            if col is None or not code:
                msg = f"filtro {item!r} inválido; use dimensão:código ({list(_EXECUTION_COLUMNS)})"
                raise SemanticError(msg)
            joins.update(col.joins)
            where.append(f"coalesce({col.code}, '{MISSING_CODE}') = $f{i}")
            params[f"f{i}"] = code
        tables = {"f": FACTS["C"]}
        join_sql = ""
        for alias in sorted(joins):
            name, table, on = _JOINS[alias]
            tables[name] = table
            join_sql += f" LEFT JOIN {{{{{name}}}}} {name} ON {on}"
        sums = ", ".join(f"sum(f.{p}) AS {p}" for p in _PHASES)
        totals = ", ".join(f"sum({p}) OVER () AS t_{p}" for p in _PHASES)
        grouped = (
            f"SELECT coalesce({column.code}, '{MISSING_CODE}') AS key, "
            f"max({column.label}) AS label, {sums} FROM {{{{f}}}} f{join_sql} "
            f"WHERE {' AND '.join(where)} GROUP BY 1"
        )
        rows = self._rows(
            ctx,
            f"WITH g AS ({grouped}) SELECT *, count(*) OVER () AS n, {totals} FROM g "
            f"ORDER BY paid DESC, key LIMIT {PAGE_SIZE} OFFSET $offset",
            tables,
            params,
        )
        # Página vazia não significa ausência de execução no restante do recorte.
        count = (
            rows[0]
            if rows
            else self._rows(
                ctx,
                "SELECT count(*) AS n, "
                + ", ".join(f"sum({p}) AS t_{p}" for p in _PHASES)
                + f" FROM ({grouped})",
                tables,
                {key: value for key, value in params.items() if key != "offset"},
            )[0]
        )
        n = int(count["n"] or 0)
        total = ExecutionRowOut(
            category_code="total",
            label="Total",
            **{p: _float(count[f"t_{p}"]) for p in _PHASES},
        )
        return ContasExecutionOut(
            dimension=dimension,
            page=page,
            page_size=PAGE_SIZE,
            pages=min(MAX_PAGES, math.ceil(n / PAGE_SIZE)),
            rows_total=n,
            total=total,
            rows=[
                ExecutionRowOut(
                    category_code=str(r["key"]),
                    label=r["label"] or "Não se aplica ou sem informação",
                    **{p: _float(r[p]) for p in _PHASES},
                )
                for r in rows
            ],
            provenance=self._provenance(ctx, "C", months, list(tables.values())),
        )


_GROUP_LABELS = {"territory": "Território", "recipient": "Favorecido"}


@dataclass(frozen=True, slots=True)
class _TableSql:
    """Consulta da tabela: SQL agrupado (com rótulo, se a ordem pede), tabelas e parâmetros."""

    named: str
    tables: dict[str, str]
    params: dict[str, Any]
    notes: list[str]
    order: str


def _table_sql(
    *,
    lens: str,
    level: str,
    where: list[str],
    group_by: str,
    filters: Sequence[str],
    sort: str,
    include_intermediaries: bool,
) -> _TableSql:
    """Monta a consulta da tabela só com fragmentos fixos; os valores vão como parâmetros."""
    columns = _TABLE_COLUMNS[lens]
    joins: set[str] = set()
    params: dict[str, Any] = {}
    for i, item in enumerate(filters):
        dim, _, code = item.partition(":")
        column = columns.get(dim)
        if column is None or not code:
            msg = f"filtro {item!r} inválido; use dimensão:código ({list(columns)})"
            raise SemanticError(msg)
        joins.update(column.joins)
        where.append(f"coalesce({column.code}, '{MISSING_CODE}') = $f{i}")
        params[f"f{i}"] = code
    notes: list[str] = []
    if group_by == "recipient":
        if not include_intermediaries:
            where.append("NOT list_contains(CAST($not_ranked AS VARCHAR[]), f.recipient_class)")
            params["not_ranked"] = list(NOT_RANKED)
            notes.append(
                "Sem lançamentos agregados, unidades federais, bancos pagadores, sigilosos e "
                "sem informação (include_intermediaries=true para incluí-los)."
            )
        key_sql, label_sql = "f.recipient_key", "NULL"
    elif group_by == "territory":
        expr = {
            "regiao": "'regiao:' || left(f.uf_code, 1)",
            "uf": "'uf:' || f.uf_code",
            "municipio": "'municipio:' || f.municipality_id",
        }[_CHILD_LEVEL[level]]
        key_sql, label_sql = f"coalesce({expr}, 'fora')", "NULL"
    else:
        column = columns[group_by]
        joins.update(column.joins)
        key_sql = f"coalesce({column.code}, '{MISSING_CODE}')"
        label_sql = f"max({column.label})"
    tables = {"f": FACTS[lens]}
    join_sql = ""
    for alias in sorted(joins):
        name, table, on = _JOINS[alias]
        tables[name] = table
        join_sql += f" LEFT JOIN {{{{{name}}}}} {name} ON {on}"
    grouped = (
        f"SELECT {key_sql} AS key, {label_sql} AS label, sum(f.value) AS value "
        f"FROM {{{{f}}}} f{join_sql} WHERE {' AND '.join(where)} GROUP BY 1"
    )
    named = grouped
    if sort == "name" and group_by == "recipient":
        # Ordenar por nome exige o rótulo antes da página.
        tables["rec"] = "dim_recipient"
        named = (
            f"SELECT g.key, r2.recipient_name AS label, g.value FROM ({grouped}) g "
            "JOIN {{rec}} r2 ON r2.recipient_key = g.key"
        )
    elif sort == "name" and group_by == "territory":
        tables["geo"] = "dim_geography"
        named = (
            f"SELECT g.key, coalesce(t.name, g.key) AS label, g.value FROM ({grouped}) g "
            "LEFT JOIN {{geo}} t ON t.geography_key = g.key"
        )
    order = "value DESC, key" if sort == "value" else "label NULLS LAST, key"
    return _TableSql(named, tables, params, notes, order)
