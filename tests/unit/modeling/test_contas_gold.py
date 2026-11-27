"""Gold das contas públicas: Silver simulada (configuração real) → Gold (ADR-0036)."""

from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from odb_lakehouse import DeltaReader
from odb_modeling import contas
from odb_modeling.builder import GoldBuild
from odb_modeling.contas_builder import ContasGoldBuilder
from odb_processing.quality import CheckStatus
from odb_processing.values import VALUE_DTYPE
from tests.gold_support import InMemoryGoldRegistry
from tests.unit.processing.test_silver_contas import ALL, Env


class GoldContas:
    def __init__(
        self, tmp_path: Path, fpm: dict[tuple[str, str, str, int], str] | None = None
    ) -> None:
        self.env = Env(tmp_path)
        if fpm is not None:
            self.env.portal.fpm.update(fpm)
        self.env.ingest(*ALL)
        runs = self.env.builder.build_many(list(ALL))
        assert all(r.status == "succeeded" for r in runs), [(r.dataset_id, r.error) for r in runs]
        self.registry = InMemoryGoldRegistry(self.env.registry)
        self.builder = ContasGoldBuilder(
            self.env.catalog,
            self.env.layout,
            self.env.builder._writer,
            self.registry,
            code_version="test",
            top_n=3,
        )

    def table(self, build: GoldBuild, name: str) -> pl.DataFrame:
        t = build.tables[name]
        return DeltaReader().scan(t.storage_uri, t.delta_version).collect()


@pytest.fixture(scope="module")
def gold(tmp_path_factory: pytest.TempPathFactory) -> tuple[GoldContas, GoldBuild]:
    env = GoldContas(tmp_path_factory.mktemp("contas"))
    return env, env.builder.build()


def _value(frame: pl.DataFrame, **where: str) -> Decimal:
    for column, wanted in where.items():
        frame = frame.filter(pl.col(column) == wanted)
    assert frame.height == 1, frame
    value: Decimal = frame["value"][0]
    return value


def test_build_succeeds_with_all_tables_and_no_failure(gold: tuple[GoldContas, GoldBuild]) -> None:
    env, build = gold
    assert build.status == "succeeded", build.error
    assert set(build.tables) == set(env.builder.contracts())
    checks = {c.check_id: c for c in env.registry.checks[build.build_id]}
    assert not [c.check_id for c in checks.values() if c.status is CheckStatus.FAIL]
    assert checks["fidelity.silver_sums"].status is CheckStatus.PASS
    assert checks["agg_contas_territory.dimensions_sum_to_total"].status is CheckStatus.PASS


def test_identical_source_lines_are_summed_not_lost(gold: tuple[GoldContas, GoldBuild]) -> None:
    env, build = gold
    fact = env.table(build, "fact_federal_transfer").filter(pl.col("period") == "2024M10")
    guarabira = fact.filter(pl.col("geography_key") == "municipio:2506301")
    assert guarabira.select("value", "source_lines", "year").rows() == [
        (Decimal("2001.00"), 2, 2024)  # as duas linhas idênticas da fonte
    ]
    state = fact.filter(pl.col("territory_status") == "sem_municipio")
    assert state.select("geography_key", "uf_code").rows() == [("uf:25", "25")]


def test_region_is_the_sum_of_states_and_brazil_of_everything(
    gold: tuple[GoldContas, GoldBuild],
) -> None:
    env, build = gold
    agg = env.table(build, "agg_contas_territory").filter(
        (pl.col("lens") == "A") & (pl.col("period") == "2024M10")
    )
    total = agg.filter(pl.col("dimension_id") == "total")
    assert _value(total, geography_key="municipio:2506301") == Decimal("2001.00")
    assert _value(total, geography_key="uf:25") == Decimal("2001.85")  # + estado sem município
    assert _value(total, geography_key="regiao:2") == Decimal("2001.85")
    assert _value(total, geography_key="uf:51") == Decimal("-12.00")  # estorno fica negativo
    assert _value(total, geography_key="brasil:1") == Decimal("1989.85")
    by_class = agg.filter(
        (pl.col("dimension_id") == "recipient_class") & (pl.col("geography_key") == "uf:25")
    )
    assert dict(by_class.select("category_label", "value").iter_rows()) == {
        "Municípios (prefeituras)": Decimal("2001.00"),
        "Estados e Distrito Federal": Decimal("0.85"),
    }


def test_ranking_excludes_intermediaries_and_follows_the_hierarchy(
    gold: tuple[GoldContas, GoldBuild],
) -> None:
    env, build = gold
    rank = env.table(build, "agg_recipient_rank").filter(pl.col("lens") == "B")
    names = env.table(build, "dim_recipient").select("recipient_key", "recipient_name")
    brazil = (
        rank.filter(pl.col("geography_key") == "brasil:1")
        .join(names, on="recipient_key")
        .sort("rank")
    )
    # Sigiloso e banco ficam fora do ranking (continuam nos totais); o exterior entra.
    assert brazil.select("rank", "recipient_name", "recipients_in_territory").rows() == [
        (1, None, 3),  # favorecido no exterior, sem nome na fonte
        (2, "ATLAS LTDA", 3),
        (3, "FULANA DE TAL", 3),
    ]
    assert brazil["value"].to_list() == [
        Decimal("938137.46"),
        Decimal("713928.60"),
        Decimal("1400.00"),
    ]
    northeast = rank.filter(pl.col("geography_key") == "uf:24").join(names, on="recipient_key")
    assert northeast["recipient_name"].to_list() == ["FULANA DE TAL"]  # sede no RN


def test_dimensions_keep_text_out_of_facts(gold: tuple[GoldContas, GoldBuild]) -> None:
    env, build = gold
    recipients = env.table(build, "dim_recipient")
    person = recipients.filter(pl.col("recipient_code") == "***.810.079-**")
    assert person.select("recipient_name", "is_natural_person", "in_payments").rows() == [
        ("FULANA DE TAL", True, True)
    ]
    bank = recipients.filter(pl.col("recipient_code") == "00000000000191")
    assert bank["cnae_section_code"].to_list() == ["K"]
    atlas = recipients.filter(pl.col("recipient_code") == "50875450000104")
    assert atlas.select("seat_municipality_name", "seat_uf").rows() == [("GUARABIRA", "PB")]
    fact = env.table(build, "fact_federal_payment_recipient")
    assert "recipient_name" not in fact.columns
    assert fact["recipient_key"].null_count() == 0


def test_latest_month_is_open_and_closed_months_are_checked(
    gold: tuple[GoldContas, GoldBuild],
) -> None:
    env, build = gold
    status = env.table(build, "agg_contas_period_status")
    assert status.select("lens", "period", "status").rows() == [
        ("A", "2024M10", "fechado"),
        ("A", "2024M11", "aberto"),
        ("B", "2024M10", "fechado"),
        ("B", "2024M11", "aberto"),
        ("C", "2024M10", "fechado"),
        ("C", "2024M11", "aberto"),
    ]
    periods = env.table(build, "dim_period")["period"].to_list()
    assert {"2024M10", "2024M11", "2024T4", "2024"} <= set(periods)


def test_fpm_equal_to_the_treasury_gets_no_complement(gold: tuple[GoldContas, GoldBuild]) -> None:
    env, build = gold
    fact = env.table(build, "fact_federal_transfer")
    assert fact["value_source"].unique().to_list() == ["cgu"]
    rec = env.table(build, "agg_fpm_reconciliation")
    assert rec.select("period", "municipality_id", "status").rows() == [
        ("2024M10", "2506301", "conferido"),
        ("2024M10", "5101837", "conferido"),  # estorno igual nas duas fontes
        ("2024M11", "2506301", "conferido"),
        ("2024M11", "5101837", "conferido"),
    ]  # janeiro do Tesouro fica fora: o mês não existe na lente A
    checks = {c.check_id: c for c in env.registry.checks[build.build_id]}
    assert checks["fpm.reconciliation"].status is CheckStatus.PASS
    assert checks["fpm.treasury_complement"].status is CheckStatus.PASS


def test_treasury_complements_the_missing_fpm(tmp_path: Path) -> None:
    """Tesouro acima da lente A em novembro: uma linha de complemento para Guarabira."""
    env = GoldContas(tmp_path, {("2033", "Guarabira", "PB", 11): "1.502.001,00"})
    build = env.builder.build()
    assert build.status == "succeeded", build.error
    fact = env.table(build, "fact_federal_transfer")
    extra = fact.filter(pl.col("value_source") == "tesouro_fpm")
    original = fact.filter(
        (pl.col("value_source") == "cgu")
        & (pl.col("period") == "2024M11")
        & (pl.col("geography_key") == "municipio:2506301")
    )
    assert extra.select("period", "geography_key", "value", "source_lines").rows() == [
        ("2024M11", "municipio:2506301", _d("1.5"), 1)
    ]
    # Mesmo favorecido, UG, ação e natureza da linha de FPM da prefeitura.
    keys = ["recipient_key", "ug_key", "action_key", "nature_key", "transfer_type"]
    assert extra.select(keys).rows() == original.select(keys).rows()
    total = env.table(build, "agg_contas_territory").filter(
        (pl.col("lens") == "A")
        & (pl.col("period") == "2024M11")
        & (pl.col("dimension_id") == "total")
        & (pl.col("geography_key") == "municipio:2506301")
    )
    assert total["value"].to_list() == [Decimal("2001.00") + _d("1.5")]
    rec = env.table(build, "agg_fpm_reconciliation").filter(
        (pl.col("period") == "2024M11") & (pl.col("municipality_id") == "2506301")
    )
    assert rec.select("status", "complement").rows() == [("complementado", _d("1.5"))]
    status = env.table(build, "agg_contas_period_status").filter(
        (pl.col("lens") == "A") & (pl.col("period") == "2024M11")
    )
    assert status["complement_value"].to_list() == [_d("1.5")]
    assert "Tesouro Nacional" in status["note"][0]


def test_unchanged_silver_skips_the_build(gold: tuple[GoldContas, GoldBuild]) -> None:
    env, build = gold
    again = env.builder.build()
    assert again.status == "skipped"
    assert {t: v.delta_version for t, v in again.tables.items()} == {
        t: v.delta_version for t, v in build.tables.items()
    }


# ------------------------------------------------------------------ funções puras


def _d(value: str) -> Decimal:
    """Milhões de reais (a tolerância por ação é de R$ 1 milhão ou 1%)."""
    return Decimal(value) * 1_000_000


def test_reconciliation_flags_missing_actions_and_incomplete_months() -> None:
    transfers = pl.DataFrame(
        {
            "period": ["202501", "202501", "202502"],
            "action_code": ["0045", "0369", "0045"],
            "value_transfers": [_d("100"), _d("10"), _d("100")],
            "action_name": ["FPM", "SALARIO-EDUCACAO", "FPM"],
            "transfer_type": ["Constitucionais e Royalties"] * 3,
        },
        schema_overrides={"value_transfers": VALUE_DTYPE},
    )
    execution = pl.DataFrame(
        {
            "period": ["202501", "202501", "202502", "202502"],
            "action_code": ["0045", "0369", "0045", "0369"],
            "paid_execution": [_d("150"), _d("10"), _d("99.5"), _d("12")],
            "payables_paid_execution": [_d("0"), _d("0"), _d("0"), _d("0")],
            "_execution_name": ["FPM", "SALARIO-EDUCACAO", "FPM", "SALARIO-EDUCACAO"],
        },
        schema_overrides={"paid_execution": VALUE_DTYPE, "payables_paid_execution": VALUE_DTYPE},
    )
    reconciliation = contas.transfer_reconciliation(transfers, execution)
    assert reconciliation.select("period", "action_code", "action_status", "shortfall").rows() == [
        ("2025M01", "0045", "abaixo_da_execucao", _d("50")),
        ("2025M01", "0369", "conferido", _d("0")),
        ("2025M02", "0045", "conferido", _d("0")),
        ("2025M02", "0369", "ausente_nas_transferencias", _d("12")),
    ]
    totals = {
        "A": pl.DataFrame(
            {"period": ["2025M01", "2025M02", "2025M03"], "value": [_d("110"), _d("100"), _d("1")]},
            schema_overrides={"value": VALUE_DTYPE},
        )
    }
    status = contas.period_status(totals, reconciliation)
    assert status.select("period", "status").rows() == [
        ("2025M01", "incompleto"),  # falta 50 de 160 (31%)
        ("2025M02", "incompleto"),  # falta 12 de 111,5 (10,8%)
        ("2025M03", "aberto"),
    ]
    assert status["missing_actions"][0].to_list() == ["FPM"]
    complements = pl.DataFrame(
        {"period": ["2025M01"], "complement_value": [Decimal("10092734000.00")]},
        schema_overrides={"complement_value": VALUE_DTYPE},
    )
    noted = contas.period_status(totals, reconciliation, complements=complements)
    assert "Inclui R$ 10,09 bi do FPM" in noted["note"][0]
    assert "Tesouro" not in noted["note"][1]


def test_territory_falls_back_to_state_then_brazil() -> None:
    frame = pl.LazyFrame(
        {
            "uf": ["PB", "PB", "EX", "-1", "MU"],
            "municipality_id": ["2506301", None, None, None, None],
        }
    )
    out = contas.with_territory(frame).collect()
    assert out.select("uf_code", "geography_key").rows() == [
        ("25", "municipio:2506301"),
        ("25", "uf:25"),
        (None, "brasil:1"),
        (None, "brasil:1"),
        (None, "brasil:1"),
    ]
    assert contas.gold_period("p").meta.output_name() == "p"


def _lens_a(rows: list[tuple[str, str | None, str, str, str]]) -> pl.LazyFrame:
    """Lente A mínima: (mês, município, ação, classe, valor em milhões)."""
    return pl.LazyFrame(
        {
            "period": [r[0] for r in rows],
            "uf": ["PB"] * len(rows),
            "municipality_id": [r[1] for r in rows],
            "territory_status": ["municipio"] * len(rows),
            "recipient_code": [f"cnpj-{r[1]}" for r in rows],
            "recipient_name": [f"MUNICIPIO {r[1]}" for r in rows],
            "recipient_class": [r[3] for r in rows],
            "action_code": [r[2] for r in rows],
            "organ_code": ["-1"] * len(rows),
            "value": [_d(r[4]) for r in rows],
        },
        schema_overrides={"value": VALUE_DTYPE},
    )


def _treasury(rows: list[tuple[str, str, str]]) -> pl.LazyFrame:
    return pl.LazyFrame(
        {
            "period": [r[0] for r in rows],
            "municipality_id": [r[1] for r in rows],
            "value": [_d(r[2]) for r in rows],
        },
        schema_overrides={"value": VALUE_DTYPE},
    )


def test_fpm_complement_only_in_months_below_the_treasury() -> None:
    lens_a = _lens_a(
        [
            ("202501", "2506301", "0045", "municipio", "10"),
            ("202501", "2507507", "0045", "municipio", "5"),
            ("202502", "2506301", "0045", "municipio", "10"),
            ("202502", "2506301", "0045", "empresa", "3"),  # não serve de modelo
            ("202502", "2506301", "0369", "municipio", "1"),  # outra ação
            ("202503", "2506301", "0045", "municipio", "10"),
        ]
    )
    treasury = _treasury(
        [
            ("202412", "2506301", "9"),  # mês fora da lente A
            ("202501", "2506301", "10"),
            ("202501", "2507507", "5"),
            ("202502", "2506301", "16"),  # 13 na lente A: falta 3
            ("202502", "2507507", "5"),  # ausente na lente A: falta 5
            ("202503", "2506301", "10.5"),  # 0,5 abaixo da tolerância: não complementa
        ]
    )
    out = contas.fpm_complement(lens_a, treasury)
    assert out.negative.is_empty()
    assert out.without_template.is_empty()
    assert out.rows.select(
        "period", "municipality_id", "recipient_code", "recipient_class", "value", "value_source"
    ).rows() == [
        ("202502", "2506301", "cnpj-2506301", "municipio", _d("3"), "tesouro_fpm"),
        ("202502", "2507507", "cnpj-2507507", "municipio", _d("5"), "tesouro_fpm"),  # de jan.
    ]
    assert out.rows["uf"].to_list() == ["PB", "PB"]
    assert out.reconciliation.select("period", "municipality_id", "status").rows() == [
        ("2025M01", "2506301", "conferido"),
        ("2025M01", "2507507", "conferido"),
        ("2025M02", "2506301", "complementado"),
        ("2025M02", "2507507", "complementado"),
        ("2025M03", "2506301", "divergente"),
    ]


def test_fpm_complement_reports_negative_and_missing_template() -> None:
    lens_a = _lens_a(
        [
            ("202502", "2506301", "0045", "municipio", "10"),
            ("202502", "2507507", "0045", "municipio", "6"),
        ]
    )
    treasury = _treasury(
        [
            ("202502", "2506301", "20"),
            ("202502", "2507507", "5"),  # Tesouro abaixo da lente A num mês complementado
            ("202502", "2504009", "2"),  # sem nenhuma linha de FPM na lente A
        ]
    )
    out = contas.fpm_complement(lens_a, treasury)
    assert out.negative.rows() == [("202502", "2507507", -_d("1"))]
    assert out.without_template.rows() == [("202502", "2504009")]
    assert out.rows["municipality_id"].to_list() == ["2506301", "2507507"]
