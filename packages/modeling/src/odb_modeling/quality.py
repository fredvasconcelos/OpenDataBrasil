"""Verificações de qualidade da Gold (§16).

Severidade, como na Silver:

* ``fail`` bloqueia a escrita e a publicação: contrato, chaves, integridade
  referencial, unidade divergente da publicada, categoria sem hierarquia
  declarada, nível territorial desconhecido, nota oficial não resolvida e
  divergência entre Gold e Silver;
* ``warn`` é registrado, sem bloquear: divergências da reconciliação por
  categoria, divergências entre tabelas sobrepostas (consistência) e
  territórios ausentes da referência.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

import polars as pl

from odb_modeling.geometry import GeometryReport
from odb_modeling.model import (
    NO_BREAKDOWN,
    SIDRA_LEVELS,
    DatasetInfo,
    category_column,
    dimension_map,
)
from odb_processing.contracts import Contract
from odb_processing.quality import CheckResult, CheckStatus, check_contract, check_required
from odb_processing.values import QUANTITATIVE
from odb_semantics import LEVELS, SemanticCatalog

_QUANT = [s.value for s in QUANTITATIVE]


def _result(check_id: str, problems: Any, ok_message: str, fail_message: str) -> CheckResult:
    if problems:
        return CheckResult(check_id, CheckStatus.FAIL, fail_message, observed=problems)
    return CheckResult(check_id, CheckStatus.PASS, ok_message)


# ------------------------------------------------------------------ entradas


def input_checks(
    selected: pl.DataFrame,
    catalog: SemanticCatalog,
    datasets: Mapping[str, DatasetInfo],
    pending_report: Sequence[Mapping[str, object]],
    fixed_problems: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
) -> list[CheckResult]:
    """Conferência do catálogo semântico contra os dados Silver.

    ``selected`` já vem sem as dimensões de categoria fixa; ``fixed_problems``
    traz as divergências encontradas ao retirá-las.
    """
    results: list[CheckResult] = []
    fixed_count = sum(len(f.fixed_categories) for f in catalog.facts)
    results.append(
        _result(
            "semantics.fixed_categories",
            dict(fixed_problems or {}),
            f"{fixed_count} dimensões de categoria fixa conferem com a Silver",
            "dimensões de categoria fixa com outra categoria ou ausentes na Silver",
        )
    )
    present = {
        (r["table_id"], r["variable_id"]): r
        for r in selected.group_by("table_id", "variable_id")
        .agg(
            # Sem valor ("...", não disponível), a fonte não informa unidade: só os
            # valores publicados definem a unidade da variável.
            pl.col("unit_name")
            .filter(~((pl.col("unit_name") == "") & (pl.col("value_status") == "not_available")))
            .unique()
            .sort()
            .alias("units"),
            pl.len().alias("n"),
        )
        .iter_rows(named=True)
    }
    missing = []
    unit_problems = {}
    for ind in catalog.indicators:
        row = present.get((datasets[ind.dataset].table_id, ind.variable))
        if row is None:
            missing.append(ind.id)
        elif row["units"] != [ind.unit]:
            unit_problems[ind.id] = {"published": row["units"], "declared": ind.unit}
    results.append(
        _result(
            "semantics.variables_present",
            missing,
            f"{len(catalog.indicators)} indicadores com observações na Silver",
            "indicadores sem observações na Silver",
        )
    )
    results.append(
        _result(
            "semantics.unit",
            unit_problems,
            "unidades conferem com as publicadas",
            "unidade declarada difere da publicada",
        )
    )

    levels = set(selected["territorial_level"].unique().to_list()) - set(SIDRA_LEVELS)
    results.append(
        _result(
            "semantics.territorial_level",
            sorted(levels),
            "níveis territoriais mapeados",
            "níveis territoriais sem correspondência no modelo",
        )
    )

    dims = dimension_map(catalog)
    exploded = (
        selected.select("indicator_id", "fact_table", "classification_key", "classifications")
        .unique(["indicator_id", "classification_key"])
        .drop("classification_key")
        .explode("classifications", empty_as_null=False)
        .drop_nulls("classifications")
        .unnest("classifications")
        .unique(["fact_table", "dimension", "category_id"])
    )
    unknown_dims = sorted(set(exploded["dimension"].unique().to_list()) - set(dims))
    results.append(
        _result(
            "semantics.classification",
            unknown_dims,
            "dimensões da Silver declaradas no catálogo",
            "dimensões da Silver sem classificação declarada",
        )
    )
    wrong_fact: dict[str, list[str]] = {}
    undeclared: dict[str, list[str]] = {}
    for fact in catalog.facts:
        rows = exploded.filter(pl.col("fact_table") == fact.id)
        observed = {dims.get(d) for d in rows["dimension"].unique().to_list()}
        if observed != set(fact.classifications) and rows.height:
            wrong_fact[fact.id] = sorted(str(o) for o in observed)
        for cid in fact.classifications:
            cls = catalog.classification(cid)
            cats = set(
                rows.filter(pl.col("dimension") == cls.silver_dimension)["category_id"].to_list()
            )
            extra = sorted(cats - cls.declared())
            if extra:
                undeclared[cid] = sorted(set(undeclared.get(cid, [])) | set(extra))
    results.append(
        _result(
            "semantics.fact_classifications",
            wrong_fact,
            "classificações dos fatos conferem com a Silver",
            "classificações observadas diferem das declaradas no fato",
        )
    )
    results.append(
        _result(
            "semantics.category_hierarchy",
            undeclared,
            "todas as categorias observadas têm posição na hierarquia",
            "categorias observadas sem posição na hierarquia declarada",
        )
    )
    problems = [r for r in pending_report if r.get("problem")]
    applied = [r for r in pending_report if r.get("applied")]
    results.append(
        CheckResult(
            "notes.pending_installation",
            CheckStatus.FAIL if problems else CheckStatus.PASS,
            (
                "notas não resolvidas nos dados"
                if problems
                else f"{len(applied)} notas aplicadas, "
                f"{len(pending_report) - len(applied)} sem nível municipal nos dados"
            ),
            observed=problems or None,
            details={"report": list(pending_report)},
        )
    )
    return results


# ------------------------------------------------------------------ tabelas


def table_checks(name: str, frame: pl.DataFrame, contract: Contract) -> list[CheckResult]:
    """Contrato, nulos obrigatórios e chave única de uma tabela Gold."""
    contract_result = check_contract(frame, contract)
    results = [
        CheckResult(
            f"{name}.{contract_result.check_id}",
            contract_result.status,
            contract_result.message,
            details=contract_result.details,
        )
    ]
    if contract_result.status is CheckStatus.FAIL:
        return results
    required = check_required(frame, contract)
    results.append(
        CheckResult(
            f"{name}.{required.check_id}",
            required.status,
            required.message,
            observed=required.observed,
        )
    )
    duplicated = int(frame.select(contract.key).is_duplicated().sum())
    results.append(
        _result(
            f"{name}.unique.key",
            duplicated,
            f"chave {list(contract.key)} única ({frame.height} linhas)",
            f"{duplicated} linhas com chave duplicada",
        )
    )
    return results


def foreign_key(
    check_id: str, child: pl.DataFrame, column: str, parent: pl.DataFrame, parent_column: str
) -> CheckResult:
    """Valores não nulos de ``child[column]`` existem em ``parent[parent_column]``."""
    values = child[column]
    if values.dtype == pl.List(pl.String):
        values = values.explode(empty_as_null=False)
    missing = sorted(set(values.drop_nulls().unique().to_list()) - set(parent[parent_column]))
    return _result(
        check_id,
        missing[:50],
        f"{column} → {parent_column} íntegro",
        f"{len(missing)} valores de {column} sem correspondência",
    )


def geography_checks(geography: pl.DataFrame, bridge: pl.DataFrame) -> list[CheckResult]:
    """Hierarquia territorial completa para os territórios da referência."""
    results = []
    in_ref = geography.filter(pl.col("in_reference") & (pl.col("level_id") == "municipio"))
    ancestors = (
        bridge.filter(pl.col("geography_key").is_in(in_ref["geography_key"].implode()))
        .group_by("geography_key")
        .agg(pl.col("ancestor_level").n_unique().alias("n"))
    )
    incomplete = ancestors.filter(pl.col("n") != 6)["geography_key"].to_list()  # noqa: PLR2004
    results.append(
        _result(
            "geography.hierarchy",
            incomplete[:50],
            f"{in_ref.height} municípios com os 6 níveis da hierarquia",
            "municípios sem a hierarquia completa",
        )
    )
    # Recortes especiais vêm do SIDRA e não estão na DTB por definição.
    special = [lv.id for lv in LEVELS if lv.special]
    outside = geography.filter(~pl.col("in_reference") & ~pl.col("level_id").is_in(special))
    results.append(
        CheckResult(
            "geography.reference",
            CheckStatus.WARN if outside.height else CheckStatus.PASS,
            (
                f"{outside.height} territórios observados fora da referência territorial"
                if outside.height
                else "todos os territórios observados estão na referência"
            ),
            observed=outside.height,
            details={"territories": outside["geography_key"].head(200).to_list()},
        )
    )
    return results


def silver_fidelity(selected: pl.DataFrame, observations: pl.DataFrame) -> CheckResult:
    """A Gold reproduz exatamente as observações Silver (contagem e soma por indicador)."""

    def summary(frame: pl.DataFrame) -> dict[str, tuple[int, Decimal | None]]:
        return {
            r["indicator_id"]: (r["n"], r["s"])
            for r in frame.group_by("indicator_id")
            .agg(pl.len().alias("n"), pl.col("value").sum().alias("s"))
            .iter_rows(named=True)
        }

    silver, gold = summary(selected), summary(observations)
    diff = {
        k: {"silver": str(silver.get(k)), "gold": str(gold.get(k))}
        for k in set(silver) | set(gold)
        if silver.get(k) != gold.get(k)
    }
    return _result(
        "reconciliation.silver",
        diff,
        f"{observations.height} observações idênticas às da Silver",
        "Gold diverge da Silver",
    )


# ------------------------------------------------------------------ reconciliação por categoria


def category_reconciliation(
    observations: pl.DataFrame, catalog: SemanticCatalog
) -> list[CheckResult]:
    """Soma das categorias de cada partição contra o Total publicado.

    Para cada indicador aditivo, classificação e partição, compara em cada
    contexto (território, período e categorias das demais classificações):

    * partição exaustiva: a soma deve ser igual ao Total;
    * não exaustiva: a soma não pode passar do Total. A diferença (categoria
      não publicada) é informada nos detalhes.

    Só entram contextos em que o Total e todas as categorias da partição têm
    valor quantitativo. Ausências nunca viram zero.
    """
    results: list[CheckResult] = []
    for ind in catalog.indicators:
        if ind.additivity != "additive":
            continue
        rows = observations.filter(pl.col("indicator_id") == ind.id)
        for cid in catalog.fact(ind.fact).classifications:
            cls = catalog.classification(cid)
            tagged = rows.with_columns(
                category_column(cid).alias("category"),
                pl.col("breakdown_key")
                .str.split("|")
                .list.eval(pl.element().filter(~pl.element().str.starts_with(f"{cid}:")))
                .list.join("|")
                .alias("context"),
            )
            keys = ["geography_key", "period", "context"]
            for part in cls.partitions:
                parent_key = f"{cid}:{cls.parent_of(part)}"
                totals = tagged.filter(
                    (pl.col("category") == parent_key) & pl.col("value_status").is_in(_QUANT)
                ).select(*keys, pl.col("value").alias("official"))
                members = [f"{cid}:{c}" for c in part.categories]
                children = (
                    tagged.filter(pl.col("category").is_in(members))
                    .group_by(keys)
                    .agg(
                        pl.col("value").sum().alias("children_sum"),
                        pl.len().alias("n"),
                        pl.col("value_status").is_in(_QUANT).all().alias("complete"),
                    )
                )
                if children.is_empty():
                    continue
                joined = totals.join(children, on=keys, how="inner").filter(
                    pl.col("complete") & (pl.col("n") == len(members))
                )
                joined = joined.with_columns(
                    (pl.col("official") - pl.col("children_sum")).alias("residual")
                )
                if part.exhaustive:
                    bad = joined.filter(pl.col("residual") != 0)
                else:
                    bad = joined.filter(pl.col("residual") < 0)
                check_id = f"reconciliation.category.{ind.id}.{cid}.{part.id}"
                details: dict[str, Any] = {
                    "exhaustive": part.exhaustive,
                    "compared": joined.height,
                    "skipped": children.height - joined.height,
                }
                if not part.exhaustive:
                    national = joined.filter(pl.col("geography_key") == "brasil:1").sort("period")
                    details["residual_brasil"] = [
                        {
                            "period": r["period"],
                            "context": r["context"],
                            "residual": str(r["residual"]),
                        }
                        for r in national.iter_rows(named=True)
                    ]
                    details["note"] = part.note
                if bad.height:
                    details["divergent"] = [
                        {k: str(v) for k, v in r.items()}
                        for r in bad.head(200).iter_rows(named=True)
                    ]
                    results.append(
                        CheckResult(
                            check_id,
                            CheckStatus.WARN,
                            f"{bad.height} de {joined.height} totais divergem da soma "
                            "das categorias",
                            observed=bad.height,
                            expected=0,
                            details=details,
                        )
                    )
                else:
                    parent_label = "Total" if parent_key.endswith(f":{cls.total}") else parent_key
                    rule = f"= {parent_label}" if part.exhaustive else f"≤ {parent_label}"
                    results.append(
                        CheckResult(
                            check_id,
                            CheckStatus.PASS,
                            f"{joined.height} totais conferem (categorias {rule})",
                            observed=joined.height,
                            details=details,
                        )
                    )
    return results


# ------------------------------------------------------------------ consistência


def _restricted(frame: pl.DataFrame, common: Sequence[str], totals: Sequence[str]) -> pl.DataFrame:
    """Observações com as classificações não comuns no Total, e o contexto comum."""
    prefix = pl.element().str.extract(r"^([^:]+):", 1)
    parts = (
        pl.when(pl.col("breakdown_key") == NO_BREAKDOWN)
        .then(pl.lit([], dtype=pl.List(pl.String)))
        .otherwise(pl.col("breakdown_key").str.split("|"))
    )
    return (
        frame.with_columns(parts.alias("_parts"))
        .with_columns(
            pl.col("_parts")
            .list.eval(~prefix.is_in(list(common)) & ~pl.element().is_in(list(totals)))
            .list.any()
            .alias("_other"),
            pl.col("_parts")
            .list.eval(pl.element().filter(prefix.is_in(list(common))))
            .list.sort()
            .list.join("|")
            .alias("context"),
        )
        .filter(~pl.col("_other"))
        .select("geography_key", "period", "context", "value", "value_status")
    )


def consistency_checks(observations: pl.DataFrame, catalog: SemanticCatalog) -> list[CheckResult]:
    """Valores iguais entre indicadores de tabelas sobrepostas (``[[consistency]]``).

    Compara território, período e categorias das classificações comuns, com as
    demais classificações no Total. Só entram pares em que os dois lados têm
    valor quantitativo; ausências não são comparadas. Divergência gera aviso.
    """
    totals = [f"{c.id}:{c.total}" for c in catalog.classifications]
    by_id = {i.id: i for i in catalog.indicators}
    results: list[CheckResult] = []
    for pair in catalog.consistency:
        left, right = by_id[pair.indicator], by_id[pair.reference]
        common = sorted(
            set(catalog.fact(left.fact).classifications)
            & set(catalog.fact(right.fact).classifications)
        )
        keys = ["geography_key", "period", "context"]
        a = _restricted(observations.filter(pl.col("indicator_id") == left.id), common, totals)
        b = _restricted(observations.filter(pl.col("indicator_id") == right.id), common, totals)
        joined = a.join(b, on=keys, how="inner", suffix="_ref")
        both = joined.filter(
            pl.col("value_status").is_in(_QUANT) & pl.col("value_status_ref").is_in(_QUANT)
        )
        bad = both.filter(pl.col("value") != pl.col("value_ref"))
        check_id = f"consistency.{left.id}.{right.id}"
        details: dict[str, Any] = {
            "common_classifications": common,
            "compared": both.height,
            "not_comparable": joined.height - both.height,
            "note": pair.note,
        }
        if both.is_empty():
            results.append(
                CheckResult(
                    check_id,
                    CheckStatus.WARN,
                    "nenhum valor em comum para comparar",
                    observed=0,
                    details=details,
                )
            )
        elif bad.height:
            details["divergent"] = [
                {k: str(v) for k, v in r.items()} for r in bad.head(200).iter_rows(named=True)
            ]
            results.append(
                CheckResult(
                    check_id,
                    CheckStatus.WARN,
                    f"{bad.height} de {both.height} valores divergem de {right.id}",
                    observed=bad.height,
                    expected=0,
                    details=details,
                )
            )
        else:
            results.append(
                CheckResult(
                    check_id,
                    CheckStatus.PASS,
                    f"{both.height} valores iguais aos de {right.id}",
                    observed=both.height,
                    details=details,
                )
            )
    return results


# ------------------------------------------------------------------ geometria


def geometry_checks(geometry: pl.DataFrame, report: GeometryReport) -> list[CheckResult]:
    """Cobertura e validade da ``dim_geometry``.

    ``fail``: geometria vazia ou inválida depois da simplificação.
    ``warn``: territórios da ``dim_geography`` sem polígono no nível (por
    exemplo, municípios criados depois da malha). Polígonos sem território (as
    lagoas da malha municipal) são só informados.
    """
    counts = dict(geometry.group_by("level_id").len().iter_rows())
    missing = {k: v for k, v in report.missing.items() if v}
    return [
        CheckResult(
            "geometry.valid",
            CheckStatus.FAIL if report.invalid else CheckStatus.PASS,
            f"{len(report.invalid)} geometrias inválidas, vazias ou não poligonais "
            f"({len(report.repaired)} reparadas após o arredondamento)",
            observed=len(report.invalid),
            expected=0,
            details={"invalid": report.invalid[:50], "repaired": report.repaired[:200]},
        ),
        CheckResult(
            "geometry.coverage",
            CheckStatus.WARN if missing else CheckStatus.PASS,
            "territórios sem geometria: "
            + (", ".join(f"{lvl} {len(keys)}" for lvl, keys in missing.items()) or "nenhum"),
            observed=sum(len(v) for v in missing.values()),
            expected=0,
            details={
                "polygons_by_level": counts,
                "without_geometry": {k: v[:50] for k, v in missing.items()},
                "dropped_polygons": report.dropped,
                "vertices": int(geometry["vertex_count"].sum()),
                "geojson_bytes": int(geometry["geometry_geojson"].str.len_bytes().sum()),
            },
        ),
    ]
