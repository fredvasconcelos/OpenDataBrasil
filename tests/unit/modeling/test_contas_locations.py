"""Localizador da execução: detalhe original e reconciliação Decimal por chave antiga."""

from decimal import Decimal

import polars as pl
import pytest

from odb_lakehouse import DeltaReader
from odb_modeling import contas
from odb_modeling.contas_locations import (
    FACT_EXECUTION_LOCATION,
    execution_locations,
    reconcile_locations,
)
from odb_modeling.quality import table_checks
from odb_processing.quality import blocking
from odb_processing.values import VALUE_DTYPE
from tests.unit.modeling.test_contas_gold import GoldContas


@pytest.fixture(scope="module")
def source(tmp_path_factory: pytest.TempPathFactory) -> tuple[pl.DataFrame, contas.Dimensions]:
    env = GoldContas(tmp_path_factory.mktemp("localizadores"))
    build = env.builder.build()
    assert build.status == "succeeded", build.error
    run = env.registry.silver_success(env.builder.datasets()["execution"])
    assert run is not None
    assert run.delta_version is not None
    first = DeltaReader().scan(run.target_uri, run.delta_version).collect().head(1)
    parts = []
    for uf, municipality, locator, value in [
        ("PB", "GUARABIRA", "No Município de Guarabira", "100.00"),
        (None, None, "Nacional", "200.00"),
        (None, None, None, "-5.01"),
    ]:
        parts.append(
            first.with_columns(
                pl.lit(uf, pl.String).alias("uf"),
                pl.lit(municipality, pl.String).alias("municipality_name_source"),
                pl.lit(locator, pl.String).alias("locator_name"),
                *(
                    pl.lit(Decimal(value), VALUE_DTYPE).alias(name)
                    for name in contas.EXECUTION_MEASURES
                ),
            )
        )
    dims = contas.Dimensions(
        recipient=pl.DataFrame(),
        management_unit=env.table(build, "dim_management_unit"),
        budget_action=env.table(build, "dim_budget_action"),
        expense_nature=env.table(build, "dim_expense_nature"),
        amendment_author=env.table(build, "dim_amendment_author"),
    )
    return pl.concat(parts), dims


def test_localizador_nao_perde_nacional_ausente_estorno_ou_detalhe(
    source: tuple[pl.DataFrame, contas.Dimensions],
) -> None:
    silver, dims = source
    fact = execution_locations(silver.lazy(), dims)
    original = contas.execution_fact(silver.lazy(), dims)
    assert fact.height == 3
    assert reconcile_locations(fact, original)
    assert not blocking(table_checks(FACT_EXECUTION_LOCATION.name, fact, FACT_EXECUTION_LOCATION))
    assert set(fact["location_locator_name"].to_list()) == {
        "No Município de Guarabira",
        "Nacional",
        None,
    }
    assert fact["location_uf"].null_count() == 2
    assert fact["paid"].sum() == Decimal("294.99")
    assert fact.filter(pl.col("paid") < 0)["paid"].to_list() == [Decimal("-5.01")]


def test_identidade_independe_da_ordem_e_fidelidade_detecta_um_centavo(
    source: tuple[pl.DataFrame, contas.Dimensions],
) -> None:
    silver, dims = source
    first = execution_locations(silver.lazy(), dims)
    reordered = execution_locations(silver.reverse().lazy(), dims)
    assert first.sort("location_key").equals(reordered.sort("location_key"))
    changed = first.with_columns((pl.col("paid") + Decimal("0.01")).alias("paid"))
    assert not reconcile_locations(changed, contas.execution_fact(silver.lazy(), dims))
