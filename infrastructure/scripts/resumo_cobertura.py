"""Confronta o inventário de cobertura com a API, sem preencher lacunas (ADR-0040)."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl

from odb_api.coverage_alerts import historical_expected
from odb_semantics.periods import periods_at


def _expected(
    metadata: dict[str, Any], descriptors: Path, table: str, level: str, period: str
) -> tuple[int, str] | None:
    """Usa a DTB apenas no próprio ano ou uma visão histórica explícita."""
    references = [r for r in metadata["geography"] if r["in_reference"] and r["level_id"] == level]
    if len(references) == 1 and re.search(
        rf"\b{re.escape(period[:4])}\b", references[0]["reference"]
    ):
        return int(references[0]["territories"]), str(references[0]["reference"])
    return historical_expected(descriptors, table, level, period)


def _dimension_codes(
    dim: dict[str, Any],
    *,
    level: str,
    period: str,
    base: list[dict[str, Any]],
    detail: list[dict[str, Any]],
    level_periods: set[str],
) -> set[str]:
    """Diagnostica só a dimensão singular, sem fabricar cruzamentos."""
    if dim["levels"] and level not in dim["levels"]:
        return {"V1"}
    available = {r["period"] for r in detail}
    codes = {"A3"} if available and available < level_periods else set()
    selected = [r for r in detail if r["period"] == period]
    if base and not selected:
        codes.add("V2")
    baseline = {r["source_table_id"]: r["territories"] for r in base}
    allowed = {c["category_key"] for c in dim["categories"]}
    if any(
        c["territories"] < baseline.get(r["source_table_id"], 0)
        for r in selected
        for c in r.get("category_territories", [])
        if c["category_key"] in allowed
    ):
        codes.add("A3")
    return codes


def _slice_codes(
    metadata: dict[str, Any],
    descriptors: Path,
    *,
    level: str,
    period: str,
    stored: list[dict[str, Any]],
    codes: set[str],
) -> list[str]:
    """Registra referência territorial e os estados de soma parcial já publicados."""
    references = []
    for row in stored:
        reference = _expected(metadata, descriptors, str(row["source_table_id"]), level, period)
        if reference:
            references.append(reference[1])
            if 0 < row["territories"] < reference[0]:
                codes.add("A2")
        if row.get("partial_sum", 0):
            codes.add("A4")
    return references


def _variants(
    kpi: dict[str, Any],
    *,
    level: str,
    period: str,
    codes: set[str],
    stored: list[dict[str, Any]],
    indexed: dict[tuple[str, str, str], list[dict[str, Any]]],
    periods: set[str],
) -> list[tuple[str, set[str]]]:
    """Enumera detalhes singulares e pares marginais recusados, sem consultar valores."""
    variants = [("", codes)]
    for dim in kpi["dimensions"]:
        alerts = _dimension_codes(
            dim,
            level=level,
            period=period,
            base=stored,
            detail=indexed.get((kpi["indicator_id"], level, dim["classification_id"]), []),
            level_periods=periods,
        )
        variants.append((dim["classification_id"], codes | alerts if periods else codes))
    individual = dict(variants)
    names = [d["classification_id"] for d in kpi["dimensions"]]
    for size in range(2, len(names) + 1):
        for group in itertools.combinations(names, size):
            allowed = not kpi["exclusive_dimensions"] or (
                level in kpi["crossed_levels"] and any(set(group) <= set(g) for g in kpi["crossed"])
            )
            if allowed:
                # A interseção efetiva exige o planejador; não se unem marginais.
                known = set().union(*(individual[d] for d in group))
            else:
                known = {"V4"} | ({"A1"} if "A1" in codes else set())
            variants.append(("|".join(group), known))
    return variants


def summarize(directory: Path, descriptors: Path) -> None:
    """Grava classificação dos casos armazenados e ressalvas dos derivados."""
    metadata = json.loads((directory / "catalogo-api.json").read_text(encoding="utf-8"))
    base = pl.read_parquet(directory / "cobertura.parquet").to_dicts()
    details = pl.read_parquet(directory / "detalhes.parquet").to_dicts()
    bases: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    indexed: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_level: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in base:
        bases[row["indicator_id"], row["level_id"], row["period"]].append(row)
        by_level[row["indicator_id"], row["level_id"]].add(row["period"])
    for row in details:
        indexed[row["indicator_id"], row["level_id"], row["classification_id"]].append(row)
    results: list[dict[str, Any]] = []
    differences: list[dict[str, Any]] = []
    grains: list[dict[str, Any]] = []
    for kpi in metadata["kpis"]:
        indicator = kpi["indicator_id"]
        for level in kpi["levels"]:
            periods = by_level.get((indicator, level), set())
            api_periods = set(kpi["periods_by_level"].get(level, []))
            if periods != api_periods:
                differences.append(
                    dict(
                        kpi=kpi["kpi_id"],
                        level=level,
                        kind="periods",
                        gold=sorted(periods),
                        api=sorted(api_periods),
                    )
                )
            for dim in kpi["dimensions"]:
                rows = indexed.get((indicator, level, dim["classification_id"]), [])
                if rows and dim["levels"] and level not in dim["levels"]:
                    differences.append(
                        dict(
                            kpi=kpi["kpi_id"],
                            level=level,
                            kind="dimension",
                            dimension=dim["classification_id"],
                        )
                    )
            for grain in kpi["time_grains"]:
                grains.append(
                    dict(
                        kpi_id=kpi["kpi_id"],
                        level=level,
                        grain=grain["grain"],
                        periods=periods_at(sorted(periods), grain["grain"]) if periods else [],
                        derived_level=not bool(periods),
                    )
                )
            for period in kpi["periods"]:
                stored = bases.get((indicator, level, period), [])
                codes = {"A1"} if periods and periods < set(kpi["periods"]) else set()
                # Um nível derivado exige a consulta semântica, não uma soma no inventário.
                state = "stored" if periods else "derived_query_required"
                if periods and (
                    not stored or all(r["unavailable"] == r["observations"] for r in stored)
                ):
                    codes.add("V3")
                references = _slice_codes(
                    metadata, descriptors, level=level, period=period, stored=stored, codes=codes
                )
                common = dict(
                    kpi_id=kpi["kpi_id"],
                    theme_id=kpi["theme_id"],
                    level=level,
                    period=period,
                    state=state,
                    territorial_reference="|".join(sorted(set(references))) or "unverified",
                )
                variants = _variants(
                    kpi,
                    level=level,
                    period=period,
                    codes=codes,
                    stored=stored,
                    indexed=indexed,
                    periods=periods,
                )
                for dims, alerts in variants:
                    results.append(
                        {
                            **common,
                            "state": "cross_query_required"
                            if common["state"] == "stored" and "|" in dims and "V4" not in alerts
                            else common["state"],
                            "dimensions": dims,
                            "codes": "|".join(sorted(alerts)),
                            "severity": "danger"
                            if any(c.startswith("V") for c in alerts)
                            else "warning"
                            if alerts
                            else "none",
                        }
                    )
    pl.DataFrame(results).sort("kpi_id", "level", "period", "dimensions").write_csv(
        directory / "classificacao.csv"
    )
    (directory / "conferencia-api.json").write_text(
        json.dumps(differences, ensure_ascii=False, indent=2) + "\n"
    )
    (directory / "graos.json").write_text(
        json.dumps(grains, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    print(
        f"Classificação: {len(results)} recortes; divergências API / Gold: {len(differences)}",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--descriptors", type=Path, default=Path("configs/catalog/descritores"))
    arguments = parser.parse_args()
    summarize(arguments.input, arguments.descriptors)
