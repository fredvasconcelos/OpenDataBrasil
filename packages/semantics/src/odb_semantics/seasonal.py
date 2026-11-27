"""Soma da mesma parte entre anos, com cobertura explícita (ADR-0041)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from odb_semantics.periods import PeriodError, ancestor, parse_period, parts

MAX_SEASONAL_PARTS = 120
NUMERIC = frozenset(
    {"valid", "true_zero", "rounded_zero", "derived_sum", "partial_sum", "partial_period"}
)


@dataclass(frozen=True)
class SeasonalInput:
    """Parcela nativa de uma única combinação de território e categorias."""

    period: str
    value: Decimal | None
    status: str


@dataclass(frozen=True)
class SeasonalValue:
    """Parte acumulada no intervalo, sem fingir ser período de um único ano."""

    part: str
    value: Decimal | None
    status: str
    expected: int
    present: int
    missing: tuple[str, ...]
    blocked: tuple[str, ...]
    contributors: tuple[str, ...]
    input_partial: tuple[str, ...]


def native_year(year: int, grain: str) -> tuple[str, ...]:
    """Lista posições esperadas do calendário, sem fabricar valores da fonte."""
    if grain == "ano":
        return (f"{year:04d}",)
    count, marker = {"mes": (12, "M"), "trimestre": (4, "T"), "semestre": (2, "S")}[grain]
    return tuple(
        f"{year:04d}{marker}{n:02d}" if grain == "mes" else f"{year:04d}{marker}{n}"
        for n in range(1, count + 1)
    )


def seasonal_groups(native: str, target: str, start: int, end: int) -> dict[str, tuple[str, ...]]:
    """Valida frequência e intervalo antes de qualquer consulta de observações."""
    parts(native, target)
    if not 1 <= start <= end <= 9999:  # noqa: PLR2004 - limites do calendário civil
        raise PeriodError("Intervalo de anos inválido para o acumulado entre anos")
    if (end - start + 1) * len(native_year(start, native)) > MAX_SEASONAL_PARTS:
        raise PeriodError("Acumulado entre anos excede 120 parcelas nativas; reduza o intervalo")
    result: dict[str, list[str]] = {}
    for year in range(start, end + 1):
        for code in native_year(year, native):
            part = ancestor(code, target)[4:] or "ano"
            result.setdefault(part, []).append(code)
    return {key: tuple(values) for key, values in result.items()}


def _subtotal(
    expected: tuple[str, ...], index: dict[str, SeasonalInput], part: str
) -> SeasonalValue:
    missing, blocked, contributors, partial = [], [], [], []
    value = Decimal(0)
    for code in expected:
        point = index.get(code, SeasonalInput(code, None, "absent"))
        if point.value is None and point.status in {"absent", "not_available"}:
            missing.append(code)
        elif point.value is None or point.status not in NUMERIC:
            blocked.append(code)
        else:
            if not point.value.is_finite():
                raise PeriodError(f"Valor não finito na parcela {code}")
            value += point.value
            contributors.append(code)
            if point.status in {"partial_sum", "partial_period"}:
                partial.append(code)
    status = (
        "blocked_accumulation"
        if blocked
        else "absent"
        if not contributors
        else "partial_sum"
        if missing or partial
        else "derived_sum"
    )
    return SeasonalValue(
        part,
        value if contributors and not blocked else None,
        status,
        len(expected),
        len(contributors),
        tuple(missing),
        tuple(blocked),
        tuple(contributors),
        tuple(partial),
    )


def seasonal_sum(
    points: Sequence[SeasonalInput],
    *,
    native: str,
    target: str,
    start: int,
    end: int,
) -> tuple[SeasonalValue, ...]:
    """Soma parcelas conhecidas da mesma parte, preservando ausência e sigilo.

    O chamador precisa comprovar a soma temporal, a unidade e o universo. Só uma
    série pode entrar: períodos duplicados ou subtotais misturados são recusados.
    """
    groups = seasonal_groups(native, target, start, end)
    index: dict[str, SeasonalInput] = {}
    for point in points:
        if parse_period(point.period).grain != native:
            raise PeriodError("Acumulado entre anos exige parcelas do mesmo grão nativo")
        if point.period in index:
            raise PeriodError(f"Parcela {point.period} duplicada no acumulado entre anos")
        index[point.period] = point
    return tuple(_subtotal(codes, index, part) for part, codes in groups.items())
