"""Comparação entre fontes antes do uso conjunto (§15.4, ADR-0011, decisão 5).

``odb fontes comparar-obitos`` confronta os óbitos do SIM (Ministério da Saúde,
Silver ``ms``) com o Registro Civil do IBGE (tabela 2654, Silver ``ibge``), por
UF e ano. O relatório mostra a razão SIM/Registro Civil e serve para decidir se
o SIM completa a série do IBGE (mesmo conceito, cobertura compatível) ou entra
como KPI novo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import polars as pl
import typer

from odb_common.logging import configure_logging
from odb_common.settings import load_settings
from odb_common.storage import LakehouseLayout, Layer

fontes_app = typer.Typer(no_args_is_help=True, help="Comparação entre fontes (§15.4).")

UF_NAMES = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}  # fmt: skip
# Diferença máxima, em %, para tratar duas contagens como a mesma série.
EQUIVALENT_PCT = 2.0


def all_total(frame: pl.LazyFrame) -> pl.LazyFrame:
    """Linhas em que todas as classificações estão no Total (categoria "Total" ou "T")."""
    return frame.filter(
        pl.col("classifications")
        .list.eval(
            pl.element().struct.field("category_name").eq("Total")
            | pl.element().struct.field("category_id").eq("T")
        )
        .list.all()
    )


def state_totals(frame: pl.LazyFrame, table_id: str, variable_id: str) -> pl.DataFrame:
    """Total por UF e ano (e Brasil, somando as UFs quando a fonte não traz o nível)."""
    totals = (
        all_total(
            frame.filter(
                (pl.col("table_id") == table_id)
                & (pl.col("variable_id") == variable_id)
                & pl.col("territorial_level").is_in(["1", "3"])
            )
        )
        .select("territorial_level", "territory_id", "period", pl.col("value").cast(pl.Float64))
        .collect()
    )
    states = totals.filter(pl.col("territorial_level") == "3")
    if totals.filter(pl.col("territorial_level") == "1").is_empty():
        national = (
            states.group_by("period")
            .agg(pl.col("value").sum())
            .with_columns(pl.lit("1").alias("territorial_level"), pl.lit("1").alias("territory_id"))
        )
        totals = pl.concat([states, national.select(states.columns)])
    return totals


def compare(sim: pl.DataFrame, civil: pl.DataFrame) -> pl.DataFrame:
    """SIM vs. Registro Civil por território e ano, com a razão (SIM / RC, em %)."""
    keys = ["territorial_level", "territory_id", "period"]
    return (
        sim.rename({"value": "sim"})
        .join(civil.rename({"value": "registro_civil"}), on=keys, how="inner")
        .with_columns((pl.col("sim") / pl.col("registro_civil") * 100).alias("razao_pct"))
        .sort(keys)
    )


def render(table: pl.DataFrame, generated_at: str) -> str:
    """Relatório em Markdown."""
    brazil = table.filter(pl.col("territorial_level") == "1").sort("period")
    states = table.filter(pl.col("territorial_level") == "3")
    by_state = (
        states.group_by("territory_id")
        .agg(
            pl.col("razao_pct").mean().alias("media"),
            pl.col("razao_pct").min().alias("min"),
            pl.col("razao_pct").max().alias("max"),
            pl.len().alias("anos"),
        )
        .sort("media", descending=True)
    )
    gap = (states["razao_pct"] - 100).abs()
    equivalent = int((gap <= EQUIVALENT_PCT).sum())
    lines = [
        "# Óbitos: SIM (Ministério da Saúde) vs. Registro Civil (IBGE)",
        "",
        f"<!-- Gerado por `odb fontes comparar-obitos` em {generated_at}; não editar à mão. -->",
        "",
        "Comparação exigida antes de qualquer uso conjunto (§15.4, ADR-0011, decisão 5).",
        "",
        "- **SIM:** óbitos por UF de residência, Silver `SIM-DORES` (declarações de óbito,",
        "  arquivos `DO<UF><ano>.dbc` do FTP do DATASUS).",
        '- **Registro Civil:** tabela SIDRA 2654, variável 343, "Número de óbitos',
        '  ocorridos no ano" (registros em cartório), no Total das classificações.',
        "",
        f"Pares UF vs. ano comparados: {states.height}. Diferença de até {EQUIVALENT_PCT}%: "
        f"{equivalent} ({equivalent / max(states.height, 1):.0%}).",
        "",
        "## Brasil",
        "",
        "| Ano | SIM | Registro Civil | SIM / RC |",
        "|---|---:|---:|---:|",
    ]
    for r in brazil.iter_rows(named=True):
        sim, civil = f"{r['sim']:,.0f}", f"{r['registro_civil']:,.0f}"
        lines.append(
            f"| {r['period']} | {sim.replace(',', '.')} | {civil.replace(',', '.')} "
            f"| {r['razao_pct']:.1f}% |"
        )
    lines += [
        "",
        "## UFs (média da razão SIM / RC no período comparado)",
        "",
        "| UF | Média | Mínimo | Máximo | Anos |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {UF_NAMES.get(r['territory_id'], r['territory_id'])} | {r['media']:.1f}% "
        f"| {r['min']:.1f}% | {r['max']:.1f}% | {r['anos']} |"
        for r in by_state.iter_rows(named=True)
    ]
    return "\n".join(lines) + "\n"


@fontes_app.command("comparar-obitos")
def comparar_obitos(
    saida: Annotated[Path, typer.Option(help="Relatório em Markdown.")] = Path(
        "docs/data_catalog/comparacao-obitos-sim-registro-civil.md"
    ),
) -> None:
    """SIM vs. Registro Civil (tabela 2654) por UF e ano, a partir das Silvers vigentes."""
    settings = load_settings()
    configure_logging(settings.log_level)
    layout = LakehouseLayout(settings.lakehouse_root_uri)
    sim = state_totals(
        pl.scan_delta(layout.table_uri(Layer.SILVER, "ms", "sidra_observation")),
        "SIM-DORES",
        "obitos",
    )
    civil = state_totals(
        pl.scan_delta(layout.table_uri(Layer.SILVER, "ibge", "sidra_observation")), "2654", "343"
    )
    table = compare(sim, civil)
    saida.write_text(render(table, datetime.now(UTC).isoformat()), encoding="utf-8")
    typer.echo(f"{table.height} pares comparados; relatório em {saida}")
