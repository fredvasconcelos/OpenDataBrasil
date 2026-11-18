"""Hierarquia de períodos da Gold: mês, trimestre, semestre e ano (ADR-0013).

Os códigos de período da Gold são ``AAAA`` (ano), ``AAAAMmm`` (mês), ``AAAATt``
(trimestre) e ``AAAASs`` (semestre). Este módulo diz a que período maior cada um
pertence, quantas partes compõem o período maior e como rotulá-lo, por extenso e
abreviado ("1º trimestre de 2024" e "T1 2024").

A Gold (``dim_period`` e ``bridge_period_ancestor``) e a API usam as mesmas funções,
para que a agregação no tempo e os rótulos sejam iguais nos dois lados.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

# Do mais detalhado ao menos detalhado.
GRAINS = ("mes", "trimestre", "semestre", "ano")
GRAIN_LABELS = {"mes": "Mês", "trimestre": "Trimestre", "semestre": "Semestre", "ano": "Ano"}
# Meses de cada grão (o mês é a unidade comum).
_MONTHS_IN = {"mes": 1, "trimestre": 3, "semestre": 6, "ano": 12}

MONTH_NAMES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip
MONTH_SHORT = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")

_YEAR = re.compile(r"^(\d{4})$")
_MONTH = re.compile(r"^(\d{4})M(0[1-9]|1[0-2])$")
_QUARTER = re.compile(r"^(\d{4})T([1-4])$")
_SEMESTER = re.compile(r"^(\d{4})S([12])$")


class PeriodError(ValueError):
    """Código de período fora dos formatos da Gold."""


@dataclass(frozen=True, slots=True)
class Period:
    """Um período da Gold, com a posição na hierarquia e os rótulos."""

    code: str
    grain: str
    year: int
    # Primeiro e último mês do período (1 a 12).
    first_month: int
    last_month: int

    @property
    def month(self) -> int | None:
        """Mês (só no grão mensal)."""
        return self.first_month if self.grain == "mes" else None

    @property
    def quarter(self) -> int | None:
        """Trimestre a que pertence (mês e trimestre)."""
        return (self.first_month - 1) // 3 + 1 if self.grain in ("mes", "trimestre") else None

    @property
    def semester(self) -> int | None:
        """Semestre a que pertence (todos os grãos menores que o ano)."""
        return (self.first_month - 1) // 6 + 1 if self.grain != "ano" else None

    @property
    def start(self) -> date:
        """Primeiro dia."""
        return date(self.year, self.first_month, 1)

    @property
    def end(self) -> date:
        """Último dia."""
        if self.last_month == 12:  # noqa: PLR2004 - dezembro
            return date(self.year, 12, 31)
        return date(self.year, self.last_month + 1, 1) - timedelta(days=1)

    @property
    def label(self) -> str:
        """Rótulo por extenso: "janeiro de 2024", "1º trimestre de 2024", "2024"."""
        if self.grain == "mes":
            return f"{MONTH_NAMES[self.first_month - 1]} de {self.year}"
        if self.grain == "trimestre":
            return f"{self.quarter}º trimestre de {self.year}"
        if self.grain == "semestre":
            return f"{self.semester}º semestre de {self.year}"
        return str(self.year)

    @property
    def short_label(self) -> str:
        """Rótulo abreviado: "jan 2024", "T1 2024", "S1 2024", "2024"."""
        if self.grain == "mes":
            return f"{MONTH_SHORT[self.first_month - 1]} {self.year}"
        if self.grain == "trimestre":
            return f"T{self.quarter} {self.year}"
        if self.grain == "semestre":
            return f"S{self.semester} {self.year}"
        return str(self.year)


def parse_period(code: str) -> Period:
    """Interpreta um código de período da Gold."""
    if m := _MONTH.match(code):
        month = int(m[2])
        return Period(code, "mes", int(m[1]), month, month)
    if m := _QUARTER.match(code):
        first = 3 * int(m[2]) - 2
        return Period(code, "trimestre", int(m[1]), first, first + 2)
    if m := _SEMESTER.match(code):
        first = 6 * int(m[2]) - 5
        return Period(code, "semestre", int(m[1]), first, first + 5)
    if m := _YEAR.match(code):
        return Period(code, "ano", int(m[1]), 1, 12)
    msg = f"período fora dos formatos AAAA, AAAAMmm, AAAATt e AAAASs: {code!r}"
    raise PeriodError(msg)


def months_of(code: str) -> list[str]:
    """Meses (``AAAAMmm``) que compõem um período: o próprio mês, 3, 6 ou 12."""
    p = parse_period(code)
    return [f"{p.year}M{m:02d}" for m in range(p.first_month, p.last_month + 1)]


def coarser_grains(grain: str) -> tuple[str, ...]:
    """O grão e os menos detalhados que ele (mês → mês, trimestre, semestre, ano)."""
    return GRAINS[GRAINS.index(grain) :]


def parts(grain: str, target: str) -> int:
    """Quantos períodos do ``grain`` compõem um período do ``target``."""
    if target not in coarser_grains(grain):
        msg = f"{target} não é formado por períodos de {grain}"
        raise PeriodError(msg)
    return _MONTHS_IN[target] // _MONTHS_IN[grain]


def ancestor(code: str, target: str) -> str:
    """Período do grão ``target`` que contém ``code`` ("2024M05" → "2024T2")."""
    period = parse_period(code)
    parts(period.grain, target)  # valida a direção
    if target == "ano":
        return str(period.year)
    if target == "semestre":
        return f"{period.year}S{period.semester}"
    if target == "trimestre":
        return f"{period.year}T{period.quarter}"
    return code


def periods_at(codes: Iterable[str], target: str) -> list[str]:
    """Períodos do grão ``target`` que contêm algum dos ``codes``, em ordem."""
    return sorted({ancestor(c, target) for c in codes}, key=lambda c: parse_period(c).start)


def complete_periods_at(codes: Iterable[str], target: str) -> list[str]:
    """Períodos do ``target`` com todas as partes presentes em ``codes``.

    Ex.: com meses até setembro de 2026, o ano de 2026 e o 4º trimestre ficam de fora.
    """
    present: dict[str, set[str]] = {}
    grain = None
    for code in codes:
        period = parse_period(code)
        grain = grain or period.grain
        present.setdefault(ancestor(code, target), set()).add(code)
    if grain is None:
        return []
    needed = parts(grain, target)
    return [p for p in periods_at(present, target) if len(present[p]) == needed]


# ------------------------------------------------------------------ acumulado (ADR-0026)

# Regras que admitem acumular períodos: fluxos somam; variações % mensais se compõem.
# Taxas, médias, estoques e números-índice não acumulam (o botão fica desabilitado).
ACCUMULABLE = ("sum", "compound")
_OK = ("valid", "partial_period")


def accumulate(
    items: Sequence[tuple[Decimal | None, str]], rule: str
) -> tuple[Decimal | None, str]:
    """Acumulado de um território e combinação de categorias em vários períodos.

    ``sum`` soma; ``compound`` compõe variações % ((prod(1 + v/100) - 1) * 100). Um período
    sem valor deixa o acumulado sem valor (``incomplete_period``): não se completam
    lacunas. Um período em andamento marca o resultado como ``partial_period``; outro
    status (estimativa, provisório) passa adiante.
    """
    if rule not in ACCUMULABLE:
        msg = f"a regra {rule!r} não admite acumular períodos"
        raise PeriodError(msg)
    if not items or any(v is None for v, _ in items):
        return None, "incomplete_period"
    values = [v for v, _ in items if v is not None]
    if rule == "sum":
        total = sum(values, Decimal(0))
    else:
        product = Decimal(1)
        for v in values:
            product *= 1 + v / 100
        total = (product - 1) * 100
    statuses = [s for _, s in items]
    other = next((s for s in statuses if s not in _OK), None)
    status = (
        "partial_sum"
        if "partial_sum" in statuses
        else other or ("partial_period" if "partial_period" in statuses else "valid")
    )
    return total, status


def running(
    items: Sequence[tuple[str, Decimal | None, str]], rule: str, *, by_year: bool = False
) -> list[tuple[str, Decimal | None, str]]:
    """Acumulado corrente de uma série ordenada: cada período soma (ou compõe) os anteriores.

    ``by_year``: recomeça a cada ano (acumulado no ano: jan, jan+fev, …; T1, T1+T2, …).
    """
    out: list[tuple[str, Decimal | None, str]] = []
    window: list[tuple[Decimal | None, str]] = []
    year: int | None = None
    for code, value, status in items:
        current = parse_period(code).year
        if by_year and current != year:
            window = []
        year = current
        window.append((value, status))
        out.append((code, *accumulate(window, rule)))
    return out


def covers(node: str, code: str) -> bool:
    """O período ``node`` contém ``code`` (o próprio, ou um ancestral dele)?"""
    if node == code:
        return True
    try:
        return ancestor(code, parse_period(node).grain) == node
    except PeriodError:
        return False


# Nota de método de cada regra de agregação no tempo (ADR-0017). A Gold acrescenta a
# nota a todo indicador que agrega no tempo, curado ou gerado, para que o usuário saiba
# como o trimestre, o semestre e o ano foram calculados.
TIME_AGGREGATION_NOTES = {
    "sum": (
        "Método: trimestre, semestre e ano são a soma dos períodos publicados (valor "
        "derivado, ADR-0017). Período com alguma parte sem valor fica sem valor."
    ),
    "mean": (
        "Método: trimestre, semestre e ano são a média dos períodos publicados (valor "
        "derivado, ADR-0017), como o IBGE calcula os números-índice anuais. Não substitui "
        "a estimativa anual oficial quando a pesquisa publica uma."
    ),
    "last": (
        "Método: trimestre, semestre e ano são o valor do último período publicado (valor "
        "derivado, ADR-0017); para um acumulado em 12 meses, o de dezembro é o do ano."
    ),
    "compound": (
        "Método: trimestre, semestre e ano são a composição das variações mensais, "
        "(Π(1 + vᵢ/100) - 1) x 100 (valor derivado, ADR-0017). É como o IBGE obtém a "
        "variação acumulada de um índice de preços (equivale à razão dos números-índice "
        "do fim e do início do período); confere com a variação acumulada no ano "
        "publicada na própria tabela (ex.: IPCA, tabela 1737, variável 69). Referência: "
        "IBGE, Sistema Nacional de Índices de Preços ao Consumidor: métodos de cálculo "
        "(série Relatórios Metodológicos)."
    ),
}
