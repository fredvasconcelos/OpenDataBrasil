"""Verificações de qualidade da Silver (§16).

Severidade:

* ``fail``: bloqueia a escrita da Silver (contrato, nulos obrigatórios,
  unicidade, domínio de códigos, erro de conversão);
* ``warn``: registrado, sem bloquear. Inclui divergências de reconciliação
  com os totais oficiais (decisão da Fase 3: a Silver reflete a fonte
  fielmente, e o uso na Gold é decidido depois) e códigos ausentes na
  referência territorial;
* ``pass``: verificação atendida.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

import polars as pl

from odb_processing.contracts import Contract
from odb_processing.values import QUANTITATIVE, ValueStatus


class CheckStatus(StrEnum):
    """Resultado de uma verificação."""

    PASS = "pass"  # noqa: S105 - não é senha
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Resultado de uma verificação de qualidade."""

    check_id: str
    status: CheckStatus
    message: str
    observed: Any = None
    expected: Any = None
    details: Mapping[str, Any] = field(default_factory=dict)


def blocking(results: Sequence[CheckResult]) -> list[CheckResult]:
    """Verificações que impedem a escrita."""
    return [r for r in results if r.status is CheckStatus.FAIL]


# ------------------------------------------------------------------------- genéricas


def check_contract(frame: pl.DataFrame, contract: Contract) -> CheckResult:
    """O lote segue exatamente o schema do contrato."""
    expected = contract.frame_schema()
    if frame.schema == expected:
        return CheckResult(
            "schema.contract", CheckStatus.PASS, f"{contract.name} {contract.version}"
        )
    diff = {
        c: {"observed": str(frame.schema.get(c)), "expected": str(expected.get(c))}
        for c in set(frame.schema) | set(expected)
        if frame.schema.get(c) != expected.get(c)
    }
    return CheckResult(
        "schema.contract", CheckStatus.FAIL, "schema difere do contrato", details=diff
    )


def check_required(frame: pl.DataFrame, contract: Contract) -> CheckResult:
    """Colunas obrigatórias sem nulos."""
    nulls = {c: n for c in contract.required if (n := frame[c].null_count())}
    if nulls:
        return CheckResult(
            "not_null.required", CheckStatus.FAIL, "nulos em colunas obrigatórias", observed=nulls
        )
    return CheckResult("not_null.required", CheckStatus.PASS, f"{len(contract.required)} colunas")


def check_unique(frame: pl.DataFrame, contract: Contract) -> CheckResult:
    """Chave de negócio única."""
    dup = frame.select(contract.key).is_duplicated().sum()
    if dup:
        sample = (
            frame.filter(frame.select(contract.key).is_duplicated()).head(5).select(contract.key)
        )
        return CheckResult(
            "unique.key",
            CheckStatus.FAIL,
            f"{dup} linhas com chave duplicada",
            observed=dup,
            details={"key": list(contract.key), "sample": sample.rows()},
        )
    return CheckResult(
        "unique.key", CheckStatus.PASS, f"chave {list(contract.key)}", observed=frame.height
    )


# ------------------------------------------------------------------------- SIDRA

# Domínio dos códigos territoriais por nível (estrutura de códigos do IBGE).
# Recortes especiais (docs/data_catalog/ibge-niveis-territoriais.md): 131 Amazônia
# Legal; 134 Amazônia Legal de UF (código da UF); 145 Território Quilombola por UF
# (UF + 3 dígitos do território); 1145 Território Quilombola.
TERRITORY_PATTERNS = {
    "1": r"^1$",
    "2": r"^[1-5]$",
    "3": r"^[1-5]\d$",
    "6": r"^[1-5]\d{6}$",
    "131": r"^131$",
    "134": r"^[1-5]\d$",
    "145": r"^[1-5]\d{4}$",
    "1145": r"^\d{1,3}$",
}
# Pares (filho → pai) reconciliáveis e como obter o código do pai a partir do filho.
RECONCILIATION_PAIRS: tuple[tuple[str, str, pl.Expr], ...] = (
    ("6", "1", pl.lit("1")),
    ("3", "1", pl.lit("1")),
    ("2", "1", pl.lit("1")),
    ("6", "3", pl.col("territory_id").str.slice(0, 2)),
    ("3", "2", pl.col("territory_id").str.slice(0, 1)),
    ("1145", "1", pl.lit("1")),
    ("145", "1145", pl.col("territory_id").str.slice(2).cast(pl.Int64).cast(pl.String)),
    ("145", "3", pl.col("territory_id").str.slice(0, 2)),
    ("134", "131", pl.lit("131")),
)


def check_territory_domain(frame: pl.DataFrame) -> CheckResult:
    """Códigos territoriais coerentes com o nível."""
    bad: dict[str, int] = {}
    for level, pattern in TERRITORY_PATTERNS.items():
        rows = frame.filter(pl.col("territorial_level") == level)
        if rows.height and (n := rows.filter(~pl.col("territory_id").str.contains(pattern)).height):
            bad[level] = n
    if bad:
        return CheckResult(
            "domain.territory_id", CheckStatus.FAIL, "códigos fora do padrão do nível", observed=bad
        )
    return CheckResult("domain.territory_id", CheckStatus.PASS, "códigos coerentes com o nível")


def check_value_status(frame: pl.DataFrame) -> list[CheckResult]:
    """Distribuição dos estados de valor; erro de conversão bloqueia."""
    dist = dict(frame.group_by("value_status").len().sort("value_status").iter_rows())
    results = [
        CheckResult("values.status_distribution", CheckStatus.PASS, "distribuição", observed=dist)
    ]
    errors = dist.get(ValueStatus.CONVERSION_ERROR.value, 0)
    if errors:
        sample = frame.filter(pl.col("value_status") == ValueStatus.CONVERSION_ERROR.value)
        results.append(
            CheckResult(
                "values.conversion_error",
                CheckStatus.FAIL,
                f"{errors} valores não reconhecidos",
                observed=errors,
                details={"sample": sample["value_raw"].unique().head(10).to_list()},
            )
        )
    else:
        results.append(
            CheckResult("values.conversion_error", CheckStatus.PASS, "nenhum valor não reconhecido")
        )
    return results


def check_reconciliation(
    frame: pl.DataFrame, additive: Mapping[str, Literal["exact", "rounding"]]
) -> list[CheckResult]:
    """Soma dos territórios filhos contra o valor oficial publicado para o pai.

    * só entram valores quantitativos (``valid``, ``rounded_zero``,
      ``true_zero``). Ausências não são tratadas como zero;
    * ``exact``: a diferença precisa ser 0;
    * ``rounding``: tolera ``0,5 * 10**-d * (n_filhos + 1)``, em que ``d`` é o
      maior número de casas publicadas;
    * grupos com filhos sem valor quantitativo (por exemplo, ``X``, suprimido
      para não identificar o informante) são **incompletos**: a soma conhecida
      só pode ficar abaixo do total oficial. Passar dele é divergência; ficar
      abaixo é esperado e vai para os detalhes, sem aviso.
    """
    results: list[CheckResult] = []
    quantitative = [s.value for s in QUANTITATIVE]
    usable = frame.filter(pl.col("value_status").is_in(quantitative))
    present = set(frame["territorial_level"].unique().to_list())
    for variable, mode in sorted(additive.items()):
        rows = usable.filter(pl.col("variable_id") == variable)
        if rows.is_empty():
            results.append(
                CheckResult(f"reconciliation.{variable}", CheckStatus.WARN, "variável sem valores")
            )
            continue
        for child, parent, parent_code in RECONCILIATION_PAIRS:
            if not {child, parent} <= present:
                continue
            check_id = f"reconciliation.{variable}.n{child}_n{parent}"
            is_quant = pl.col("value_status").is_in(quantitative)
            sums = (
                frame.filter(
                    (pl.col("variable_id") == variable) & (pl.col("territorial_level") == child)
                )
                .with_columns(parent_code.alias("parent_id"))
                .group_by("period", "classification_key", "parent_id")
                .agg(
                    pl.col("value").filter(is_quant).sum().alias("children_sum"),
                    is_quant.sum().alias("children"),
                    (~is_quant).sum().alias("missing"),
                    pl.col("value_decimals").max().alias("decimals"),
                )
                .filter(pl.col("children") > 0)
            )
            parents = rows.filter(pl.col("territorial_level") == parent).select(
                "period",
                "classification_key",
                pl.col("territory_id").alias("parent_id"),
                pl.col("value").alias("official"),
                pl.col("value_decimals").alias("parent_decimals"),
            )
            joined = parents.join(
                sums, on=["period", "classification_key", "parent_id"], how="inner"
            )
            divergent: list[dict[str, Any]] = []
            incomplete = 0
            for r in joined.iter_rows(named=True):
                diff: Decimal = r["children_sum"] - r["official"]
                decimals = max(r["decimals"] or 0, r["parent_decimals"] or 0)
                tolerance = (
                    Decimal(0)
                    if mode == "exact"
                    else Decimal("0.5") * Decimal(10) ** -decimals * (r["children"] + 1)
                )
                if r["missing"] and diff <= tolerance:
                    incomplete += 1
                    continue
                if abs(diff) > tolerance:
                    divergent.append(
                        {
                            "period": r["period"],
                            "classification_key": r["classification_key"],
                            "parent_id": r["parent_id"],
                            "official": str(r["official"]),
                            "children_sum": str(r["children_sum"]),
                            "difference": str(diff),
                            "children": r["children"],
                            "children_without_value": r["missing"],
                        }
                    )
            compared = joined.height
            if divergent:
                periods = sorted({d["period"] for d in divergent})
                results.append(
                    CheckResult(
                        check_id,
                        CheckStatus.WARN,
                        f"{len(divergent)} de {compared} totais divergem do valor oficial "
                        f"(períodos {periods})",
                        observed=len(divergent),
                        expected=0,
                        details={
                            "mode": mode,
                            "incomplete": incomplete,
                            "divergent": divergent[:200],
                        },
                    )
                )
            else:
                suffix = (
                    f"; {incomplete} incompletos por valores sem número (soma abaixo do oficial)"
                    if incomplete
                    else ""
                )
                results.append(
                    CheckResult(
                        check_id,
                        CheckStatus.PASS,
                        f"{compared} totais conferem ({mode}){suffix}",
                        observed=compared,
                        details={"incomplete": incomplete},
                    )
                )
    return results


def check_territorial_reference(
    frame: pl.DataFrame, reference_ids: set[str] | None, reference_label: str
) -> CheckResult:
    """Municípios com valor quantitativo existem na referência territorial (DTB)."""
    check_id = "reference.municipality"
    if reference_ids is None:
        return CheckResult(check_id, CheckStatus.WARN, f"referência {reference_label} indisponível")
    municipalities = frame.filter(
        (pl.col("territorial_level") == "6")
        & (pl.col("value_status") != ValueStatus.NOT_AVAILABLE.value)
    )["territory_id"].unique()
    if municipalities.is_empty():
        return CheckResult(check_id, CheckStatus.PASS, "sem nível municipal")
    missing = sorted(set(municipalities.to_list()) - reference_ids)
    if missing:
        return CheckResult(
            check_id,
            CheckStatus.WARN,
            f"{len(missing)} municípios ausentes em {reference_label}",
            observed=len(missing),
            details={"missing": missing[:200]},
        )
    return CheckResult(
        check_id,
        CheckStatus.PASS,
        f"{municipalities.len()} municípios presentes em {reference_label}",
        observed=municipalities.len(),
    )


def sidra_checks(
    frame: pl.DataFrame,
    contract: Contract,
    additive: Mapping[str, Literal["exact", "rounding"]],
    reference_ids: set[str] | None,
    reference_label: str,
) -> list[CheckResult]:
    """Conjunto de verificações de uma tabela SIDRA."""
    contract_check = check_contract(frame, contract)
    if contract_check.status is CheckStatus.FAIL:
        return [contract_check]
    return [
        contract_check,
        check_required(frame, contract),
        check_unique(frame, contract),
        check_territory_domain(frame),
        *check_value_status(frame),
        *check_reconciliation(frame, additive),
        check_territorial_reference(frame, reference_ids, reference_label),
    ]


# ------------------------------------------------------------------------- DTB


def dtb_checks(frame: pl.DataFrame, contract: Contract) -> list[CheckResult]:
    """Verificações da DTB de municípios."""
    contract_check = check_contract(frame, contract)
    if contract_check.status is CheckStatus.FAIL:
        return [contract_check]
    results = [contract_check, check_required(frame, contract), check_unique(frame, contract)]
    inconsistent = frame.filter(
        ~pl.col("municipality_id").str.contains(r"^[1-5]\d{6}$")
        | (pl.col("municipality_id") != pl.col("uf_id") + pl.col("municipality_local_code"))
        | pl.col("region_name").is_null()
    ).height
    results.append(
        CheckResult(
            "domain.municipality_id",
            CheckStatus.FAIL if inconsistent else CheckStatus.PASS,
            f"{inconsistent} códigos inconsistentes (UF + código local)",
            observed=inconsistent,
            expected=0,
        )
    )
    ufs = frame["uf_id"].n_unique()
    results.append(
        CheckResult(
            "coverage.uf",
            CheckStatus.PASS if ufs == 27 else CheckStatus.WARN,  # noqa: PLR2004 - 26 UFs + DF
            f"{ufs} unidades da federação",
            observed=ufs,
            expected=27,
        )
    )
    return results
