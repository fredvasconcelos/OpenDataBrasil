"""Inventaria a cobertura da Gold fixada, sem alterar dados ou publicação (ADR-0040)."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import polars as pl

from odb_api.deps import build_deps
from odb_api.gold import GoldGateway, rows
from odb_api.release import ReleaseContext
from odb_query_engine import QueryResult

LARGE_DATASET_ROWS = 2_000_000


def read_details(
    *,
    gold: GoldGateway,
    ctx: ReleaseContext,
    datasets: QueryResult,
    indicators: Sequence[str],
    output: Path,
) -> pl.DataFrame:
    """Lê detalhamentos em lotes pequenos, preservando checkpoints de consultas completas."""
    detail_sql = (
        "WITH classes AS MATERIALIZED (SELECT b.breakdown_key, c.classification_id, "
        "c.category_key FROM {{breakdown}} b, unnest(b.category_keys) AS k(category_key) "
        "JOIN {{cat}} c ON c.category_key = k.category_key WHERE NOT c.is_total), "
        "selected AS MATERIALIZED (SELECT o.indicator_id, o.source_table_id, o.level_id, "
        "o.period, o.geography_key, o.value, p.classification_id, p.category_key "
        "FROM {{obs}} o JOIN classes p USING (breakdown_key) "
        "WHERE o.indicator_id = ANY(CAST($ids AS VARCHAR[])) "
        "AND o.dataset_id = ANY(CAST($datasets AS VARCHAR[])) "
        "AND o.period = ANY(CAST($periods AS VARCHAR[]))), "
        "category_counts AS (SELECT indicator_id, source_table_id, level_id, period, "
        "classification_id, category_key, count(DISTINCT geography_key) AS territories "
        "FROM selected GROUP BY ALL), "
        "minima AS (SELECT indicator_id, source_table_id, level_id, period, "
        "classification_id, min(territories) AS minimum_category_territories, "
        "list(struct_pack(category_key := category_key, territories := territories) "
        "ORDER BY category_key) AS category_territories "
        "FROM category_counts GROUP BY ALL) "
        "SELECT s.indicator_id, s.source_table_id, s.level_id, s.period, "
        "s.classification_id, count(DISTINCT s.geography_key) AS territories, "
        "count(DISTINCT s.geography_key) FILTER (WHERE s.value IS NOT NULL) AS numeric, "
        "m.minimum_category_territories, m.category_territories FROM selected s JOIN minima m "
        "USING (indicator_id, source_table_id, level_id, period, classification_id) "
        "GROUP BY ALL ORDER BY s.indicator_id, s.source_table_id, s.level_id, "
        "s.period, s.classification_id"
    )
    parts: list[pl.DataFrame] = []
    checkpoints = output / "partes"
    checkpoints.mkdir(exist_ok=True)
    fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for dataset, count, periods in datasets.rows:
        # A PAM tem 77 milhões de observações no release N2. Dividir os períodos
        # evita elevar memória/timeout da API só para executar o inventário.
        batch = max(1, min(len(periods), LARGE_DATASET_ROWS * len(periods) // count))
        for offset in range(0, len(periods), batch):
            chosen = periods[offset : offset + batch]
            identity = json.dumps(
                [
                    ctx.release_id,
                    {k: v.delta_version for k, v in ctx.release.tables.items()},
                    fingerprint,
                    dataset,
                    chosen,
                ],
                sort_keys=True,
            )
            checkpoint = checkpoints / (hashlib.sha256(identity.encode()).hexdigest() + ".parquet")
            if checkpoint.exists():
                saved = pl.read_parquet(checkpoint)
                if saved.height:
                    parts.append(saved)
                continue
            print(f"Consultando {dataset}: períodos {chosen[0]} a {chosen[-1]}", flush=True)
            detail = gold.execute(
                ctx,
                detail_sql,
                {
                    "obs": "indicator_observation",
                    "breakdown": "dim_breakdown",
                    "cat": "dim_category",
                },
                {"ids": indicators, "datasets": [dataset], "periods": chosen},
                max_rows=100_000,
            )
            if detail.truncated:
                raise RuntimeError(f"Detalhes de {dataset} excederam o limite de metadados")
            saved = pl.DataFrame(rows(detail))
            saved.write_parquet(checkpoint)
            if saved.height:
                parts.append(saved)
            print(f"Detalhes {dataset}: {len(detail.rows)} combinações", flush=True)
    details = pl.concat(parts).sort(
        "indicator_id", "source_table_id", "level_id", "period", "classification_id"
    )
    return details


def main() -> None:
    """Grava metadados de cobertura e cruza o catálogo com a descrição da API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    deps = build_deps()
    try:
        ctx = deps.resolver.current()
        print(f"Release fixado: {ctx.release_id}", flush=True)
        nav = deps.kpis.navigation(ctx)
        descriptions = [k for theme in nav.themes for sub in theme.subthemes for k in sub.kpis]
        ids = [k.kpi_id for k in descriptions]
        indicators = sorted({k.indicator_id for k in descriptions})
        datasets = deps.gold.execute(
            ctx,
            "SELECT dataset_id, count(*), list(DISTINCT period ORDER BY period) FROM {{obs}} "
            "WHERE indicator_id = ANY(CAST($ids AS VARCHAR[])) "
            "GROUP BY dataset_id ORDER BY dataset_id",
            {"obs": "indicator_observation"},
            {"ids": indicators},
        )
        coverage = deps.gold.execute(
            ctx,
            "SELECT indicator_id, source_table_id, level_id, period, "
            "count(*) AS observations, count(DISTINCT geography_key) AS territories, "
            "count(DISTINCT geography_key) FILTER (WHERE value IS NOT NULL) AS numeric, "
            "count(*) FILTER (WHERE value_status = 'suppressed') AS suppressed, "
            "count(*) FILTER (WHERE value_status IN ('absent', 'not_available')) AS unavailable, "
            "count(*) FILTER (WHERE value_status = 'partial_sum') AS partial_sum, "
            "count(*) FILTER (WHERE value_status = 'true_zero') AS true_zero, "
            "count(*) FILTER (WHERE value_status = 'not_applicable') AS not_applicable "
            "FROM {{obs}} WHERE indicator_id = ANY(CAST($ids AS VARCHAR[])) "
            "GROUP BY ALL ORDER BY indicator_id, source_table_id, level_id, period",
            {"obs": "indicator_observation"},
            {"ids": indicators},
            max_rows=100_000,
        )
        if coverage.truncated:
            raise RuntimeError("Cobertura excedeu o limite; dividir a consulta antes de concluir")
        table = rows(coverage)
        pl.DataFrame(table).write_parquet(args.output / "cobertura.parquet")
        print(f"Cobertura: {len(table)} combinações, {coverage.elapsed_ms:.0f} ms", flush=True)
        geo = deps.gold.execute(
            ctx,
            "SELECT level_id, reference, in_reference, count(*) AS territories "
            "FROM {{geo}} GROUP BY ALL ORDER BY level_id, reference, in_reference",
            {"geo": "dim_geography"},
        )
        metadata: dict[str, Any] = {
            "release_id": ctx.release_id,
            "kpis": [k.model_dump(mode="json") for k in descriptions],
            "geography": rows(geo),
            "tables": {k: v.delta_version for k, v in ctx.release.tables.items()},
        }
        (args.output / "catalogo-api.json").write_text(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        details = read_details(
            gold=deps.gold, ctx=ctx, datasets=datasets, indicators=indicators, output=args.output
        )
        details.write_parquet(args.output / "detalhes.parquet")
        hashes = {
            name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
            for name in ("cobertura.parquet", "detalhes.parquet", "catalogo-api.json")
        }
        (args.output / "sha256.json").write_text(
            json.dumps(hashes, sort_keys=True, indent=2) + "\n"
        )
        print(f"Inventário gravado para {len(ids)} KPIs", flush=True)
    finally:
        deps.close()


if __name__ == "__main__":
    main()
