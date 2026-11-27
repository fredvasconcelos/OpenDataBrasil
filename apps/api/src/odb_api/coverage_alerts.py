"""Diagnósticos de cobertura do recorte, sem recalcular valores (ADR-0040)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from odb_api.schemas import CoverageAlertOut, CoverageAlertParams, DimensionOut


@dataclass(frozen=True)
class CoverageCell:
    """Presença de uma célula já selecionada pelo planejador semântico."""

    territory: str
    period: str
    categories: tuple[str, ...]
    status: str
    has_value: bool
    table: str | None


@lru_cache(maxsize=256)
def historical_expected(
    directory: Path, table: str, level: str, period: str
) -> tuple[int, str] | None:
    """Lê somente visões nacionais genéricas com intervalo histórico explícito.

    Contagens atuais de um descritor não provam o universo de 2008. Também não
    se atribui nome a subconjunto pela coincidência de sua contagem com capitais.
    """
    if level != "municipio" or not table.isdecimal() or not period[:4].isdecimal():
        return None
    path = directory / f"t{table}.json"
    if not path.is_file():
        return None
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    year = int(period[:4])
    matches: list[tuple[int, str]] = []
    for vision in descriptor.get("VisoesTerritoriais", []):
        name = str(vision.get("Nome", ""))
        dated = re.fullmatch(
            r"Município, em ordem de (?:código de UF e código de Município|"
            r"nome de UF e nome de Município|código de UF e nome de Município) - (\d{4})-(\d{4})",
            name,
        )
        if dated and int(dated[1]) <= year <= int(dated[2]):
            count = int(vision["QuantidadeUnidades"])
            matches.append((count, f"sidra:t{table}:visao:{vision['Id']}"))
    if not matches or len({n for n, _ in matches}) != 1:
        return None
    return sorted(matches)[0]


def _partial_categories(
    cells: Sequence[CoverageCell], index: int, total_key: str
) -> dict[str, tuple[int, int]]:
    """Compara categorias com o Total do mesmo período e cruzamento publicado."""
    # Não se unem marginais: cada comparação mantém as outras categorias fixas.
    groups: dict[tuple[str, tuple[str, ...]], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for cell in cells:
        group = (cell.period, cell.categories[:index] + cell.categories[index + 1 :])
        groups[group][cell.categories[index]].add(cell.territory)
    partial: dict[str, tuple[int, int]] = {}
    for (period, _), cats in groups.items():
        baseline = cats.get(total_key, set())
        sizes = [len(v) for k, v in cats.items() if k != total_key]
        if baseline and sizes and min(sizes) < len(baseline):
            previous = partial.get(period)
            pair = (min(sizes), len(baseline))
            if previous is None or pair[0] / pair[1] < previous[0] / previous[1]:
                partial[period] = pair
    return partial


def _territories(cells: Sequence[CoverageCell]) -> dict[tuple[str, str], set[str]]:
    """Conta presença uma vez por território, fonte e período."""
    territories: dict[tuple[str, str], set[str]] = defaultdict(set)
    for cell in cells:
        if cell.table:
            territories[(cell.table, cell.period)].add(cell.territory)
    return territories


def coverage_alerts(
    *,
    level: str,
    periods: Sequence[str],
    level_periods: Sequence[str],
    dimensions: Sequence[DimensionOut],
    active: Sequence[str],
    detail_periods: Mapping[str, Sequence[str]],
    cells: Sequence[CoverageCell],
    expected: Mapping[tuple[str, str], tuple[int, str]],
    selected_periods: Sequence[str] = (),
    invalid_cross: bool = False,
) -> list[CoverageAlertOut]:
    """Classifica disponibilidade; sigilo e zero continuam sendo observações.

    A2 compara presença territorial, não proporção de valores numéricos: o sigilo
    e os estados especiais de C10 não viram automaticamente ausência territorial.
    A3 compara categorias com o Total publicado no mesmo período e cruzamento.
    """
    alerts: list[CoverageAlertOut] = []

    def add(
        code: Literal["A1", "A2", "A3", "A4", "V1", "V2", "V3", "V4"], **params: object
    ) -> None:
        alerts.append(
            CoverageAlertOut(
                code=code,
                severity="danger" if code.startswith("V") else "warning",
                params=CoverageAlertParams.model_validate({"level": level, **params}),
            )
        )

    if set(level_periods) < set(periods):
        add("A1", available_periods=sorted(level_periods))
    if invalid_cross:
        add("V4", dimensions=list(active))
        return sorted(alerts, key=lambda a: (a.severity != "danger", a.code))

    by_id = {d.classification_id: d for d in dimensions}
    for i, dim in enumerate(active):
        definition = by_id[dim]
        tables = definition.source_table_ids
        common = {"dimension": dim, "tables": tables}
        if definition.levels and level not in definition.levels:
            add("V1", **common, available_levels=definition.levels)
            continue
        detail = detail_periods.get(dim, ())
        if detail and set(detail) < set(level_periods):
            add("A3", **common, available_periods=sorted(detail))
        non_total = [c for c in cells if c.categories[i] != definition.total_category_key]
        if cells and not non_total:
            add("V2", **common)
            continue
        partial = _partial_categories(cells, i, definition.total_category_key)
        for period, (observed, total) in sorted(partial.items()):
            add(
                "A3",
                **common,
                periods=[period],
                observed=observed,
                expected=total,
                reference="published_total",
            )

    present_periods = {
        c.period for c in cells if c.has_value or c.status not in {"absent", "not_available"}
    }
    missing_periods = set(selected_periods or level_periods) - present_periods
    if missing_periods or not cells:
        add("V3", periods=sorted(missing_periods))
    if any(c.status == "partial_sum" for c in cells):
        add("A4", periods=sorted({c.period for c in cells if c.status == "partial_sum"}))
    territories = _territories(cells)
    for (table, period), present in sorted(territories.items()):
        reference = expected.get((table, period))
        if reference and 0 < len(present) < reference[0]:
            add(
                "A2",
                tables=[table],
                periods=[period],
                observed=len(present),
                expected=reference[0],
                reference=reference[1],
            )
    # A ordem faz parte do contrato: vermelho primeiro; estável entre requisições.
    return sorted(
        alerts, key=lambda a: (a.severity != "danger", a.code, a.params.model_dump_json())
    )
