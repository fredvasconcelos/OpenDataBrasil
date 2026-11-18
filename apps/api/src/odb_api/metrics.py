"""Métricas de acesso do portal (ADR-0027, item 7): período, supressão e cache.

Lê as somas diárias do banco ``odb_metrics`` (papel ``odb_metrics_reader``). Regras:

- **Supressão abaixo de 5** (mantenedor, 2026-11-17), feita aqui e nunca no navegador:
  de 1 a 4 visualizações, ``views`` vai ``null`` e ``status`` ``"suprimido"``.
- Sem supressão complementar (pendência na ADR-0027): com um único lugar suprimido num
  recorte, o valor sai por subtração do total do nível acima. A página diz "menos de 5"
  para todo suprimido, o que deixaria de ser verdade com a complementar.
- Local desconhecido aparece como item próprio (``pais:ZZ``, ``regiao:0``, ``uf:0``),
  nunca distribuído entre lugares.
- Sem coleta (banco não configurado ou vazio): ``NotFoundError`` → 404, e a página diz
  que a coleta ainda não começou.
- As respostas não entram no cache por release (dado mutável): cache próprio de 5 min,
  o ciclo do agregador.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from odb_api.countries import COUNTRY_NAMES
from odb_api.gold import NotFoundError
from odb_api.schemas import (
    MetricsDatasetOut,
    MetricsDatasetsOut,
    MetricsGeoItemOut,
    MetricsGeoOut,
    MetricsPeriodOut,
    MetricsSummaryOut,
)
from odb_catalog.access_metrics import (
    REGION_NAMES,
    UF_NAMES,
    UNKNOWN_COUNTRY,
    UNKNOWN_UF,
    MetricsReader,
    region_of,
)

TZ = ZoneInfo("America/Sao_Paulo")
SUPPRESSION_THRESHOLD = 5
MAX_CUSTOM_DAYS = 366
CACHE_TTL_S = 300.0
MAX_DATASETS = 50
UNKNOWN_PLACE = "Não identificado"
UNKNOWN_STATE = "Estado não identificado"

PeriodKey = Literal["7d", "30d", "12m", "custom"]
GeoLevel = Literal["pais", "regiao", "uf"]
Sort = Literal["views", "downloads"]
Status = Literal["ok", "suprimido", "sem_acessos"]


class MetricsQueryError(ValueError):
    """Parâmetros inválidos (período, nível ou recorte)."""


@dataclass(frozen=True)
class Period:
    """Período fechado nas duas pontas, em dias de Brasília."""

    start: date
    end: date

    def out(self) -> MetricsPeriodOut:
        """Forma da resposta."""
        return MetricsPeriodOut.model_validate(
            {"from": self.start.isoformat(), "to": self.end.isoformat()}
        )


def resolve_period(period: PeriodKey, start: date | None, end: date | None, today: date) -> Period:
    """Datas reais do período pedido. ``today`` é o dia corrente em Brasília (incluído)."""
    if period == "custom":
        if start is None or end is None:
            raise MetricsQueryError("período custom exige from e to (AAAA-MM-DD)")
        if start > end:
            raise MetricsQueryError("from deve ser anterior ou igual a to")
        if (end - start).days + 1 > MAX_CUSTOM_DAYS:
            raise MetricsQueryError(f"o período personalizado vai até {MAX_CUSTOM_DAYS} dias")
        if end > today:
            raise MetricsQueryError("to não pode ser posterior a hoje")
        return Period(start, end)
    if start is not None or end is not None:
        raise MetricsQueryError("from e to só valem com period=custom")
    if period == "7d":
        return Period(today - timedelta(days=6), today)
    if period == "30d":
        return Period(today - timedelta(days=29), today)
    # 12 meses: do dia seguinte ao mesmo dia do ano anterior até hoje.
    try:
        year_ago = today.replace(year=today.year - 1)
    except ValueError:  # 29 de fevereiro
        year_ago = today.replace(year=today.year - 1, day=28)
    return Period(year_ago + timedelta(days=1), today)


@dataclass(frozen=True)
class _Place:
    key: str
    name: str
    views: int


def suppress(places: Sequence[_Place]) -> list[MetricsGeoItemOut]:
    """Itens da resposta: de 1 a 4 visualizações, ``views`` ``null`` e ``"suprimido"``.

    ``share_pct`` é calculado sobre o total do recorte inteiro (suprimidos incluídos).
    """
    total = sum(p.views for p in places)
    items = []
    for p in places:
        status: Status
        if p.views == 0:
            status, views, share = "sem_acessos", 0, 0.0
        elif p.views < SUPPRESSION_THRESHOLD:
            status, views, share = "suprimido", None, None
        else:
            status, views = "ok", p.views
            share = round(100 * p.views / total, 1) if total else 0.0
        items.append(
            MetricsGeoItemOut(
                geography_key=p.key, name=p.name, views=views, share_pct=share, status=status
            )
        )
    return items


def kpi_titles(navigation_json: bytes) -> dict[str, tuple[str, str]]:
    """``kpi_id`` → (título, tema), da navegação serializada do release ativo."""
    nav: dict[str, Any] = json.loads(navigation_json)
    out: dict[str, tuple[str, str]] = {}
    for theme in nav.get("themes", []):
        for sub in theme.get("subthemes", []):
            for kpi in sub.get("kpis", []):
                out.setdefault(str(kpi["kpi_id"]), (str(kpi["label"]), str(theme["label"])))
    return out


def _regions(ufs: Mapping[int, int]) -> list[_Place]:
    """As 5 Grandes Regiões (com zero) e, havendo, o Brasil sem UF identificada."""
    by_region = dict.fromkeys(REGION_NAMES, 0)
    unknown = 0
    for uf, n in ufs.items():
        region = region_of(uf)
        if region:
            by_region[region] += n
        else:
            unknown += n
    out = [_Place(f"regiao:{r}", REGION_NAMES[r], n) for r, n in by_region.items()]
    if unknown:
        out.append(_Place(f"regiao:{UNKNOWN_UF}", UNKNOWN_STATE, unknown))
    return out


def _ufs(ufs: Mapping[int, int], region: int | None) -> list[_Place]:
    """Todas as UFs do recorte (com zero, para o mapa pintar)."""
    out = [
        _Place(f"uf:{uf}", name, ufs.get(uf, 0))
        for uf, name in UF_NAMES.items()
        if region is None or region_of(uf) == region
    ]
    if region is None and ufs.get(UNKNOWN_UF, 0):
        out.append(_Place(f"uf:{UNKNOWN_UF}", UNKNOWN_STATE, ufs[UNKNOWN_UF]))
    return out


class MetricsService:
    """Consultas da página Métricas, com cache de 5 minutos por processo."""

    def __init__(
        self,
        reader: MetricsReader,
        *,
        ttl_s: float = CACHE_TTL_S,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] | None = None,
    ) -> None:
        """``today`` e ``clock`` são injetáveis para os testes."""
        self._reader = reader
        self._ttl = ttl_s
        self._clock = clock
        self._today = today or (lambda: datetime.now(TZ).date())
        self._cache: dict[tuple[object, ...], tuple[float, object]] = {}
        self._lock = threading.Lock()

    def _cached(self, key: tuple[object, ...], build: Callable[[], object]) -> object:
        now = self._clock()
        with self._lock:
            found = self._cache.get(key)
            if found is not None and found[0] > now:
                return found[1]
        value = build()
        with self._lock:
            # Descarta o que expirou para o dicionário não crescer sem limite.
            for k in [k for k, (exp, _) in self._cache.items() if exp <= now]:
                del self._cache[k]
            self._cache[key] = (now + self._ttl, value)
        return value

    def titles(
        self, release_id: str, build: Callable[[], dict[str, tuple[str, str]]]
    ) -> dict[str, tuple[str, str]]:
        """Títulos e temas dos indicadores do release (montados uma vez por ciclo)."""
        found = self._cached(("titles", release_id), build)
        assert isinstance(found, dict)  # noqa: S101
        return found

    def today(self) -> date:
        """Dia corrente em Brasília."""
        return self._today()

    def _started(self) -> date:
        started = self._cached(("started",), self._reader.collection_started)
        if not isinstance(started, date):
            msg = "a coleta de acessos ainda não começou"
            raise NotFoundError(msg)
        return started

    def summary(self, period: Period) -> MetricsSummaryOut:
        """Totais do período."""
        started = self._started()
        totals = self._cached(
            ("totals", period), lambda: self._reader.totals(period.start, period.end)
        )
        countries = self._cached(
            ("countries", period), lambda: self._reader.views_by_country(period.start, period.end)
        )
        assert isinstance(totals, dict)  # noqa: S101
        assert isinstance(countries, dict)  # noqa: S101
        return MetricsSummaryOut(
            period=period.out(),
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            collection_started_at=datetime.combine(started, dtime(0), TZ).isoformat(),
            views=int(totals.get("page_view", 0)),
            kpi_opens=int(totals.get("kpi_open", 0)),
            downloads=int(totals.get("download", 0)),
            countries=sum(1 for c, n in countries.items() if c != UNKNOWN_COUNTRY and n > 0),
            api_calls=None,
        )

    def geo(self, level: GeoLevel, within: str | None, period: Period) -> MetricsGeoOut:
        """Visualizações por País, Grande Região ou Estado."""
        self._started()
        places = self._places(level, within, period)
        return MetricsGeoOut(
            level=level, within=within, period=period.out(), items=suppress(places)
        )

    def _places(self, level: GeoLevel, within: str | None, period: Period) -> list[_Place]:
        if level == "pais":
            if within is not None:
                raise MetricsQueryError("level=pais não aceita within")
            return self._countries(period)
        ufs = self._cached(
            ("ufs", period), lambda: self._reader.views_by_uf(period.start, period.end)
        )
        assert isinstance(ufs, dict)  # noqa: S101
        if level == "regiao":
            if within != "pais:BR":
                raise MetricsQueryError("level=regiao exige within=pais:BR")
            return _regions(ufs)
        if within == "pais:BR":
            return _ufs(ufs, None)
        if within and within.startswith("regiao:") and within[7:].isdigit():
            region = int(within[7:])
            if region in REGION_NAMES:
                return _ufs(ufs, region)
        raise MetricsQueryError("level=uf exige within=pais:BR ou within=regiao:N (1 a 5)")

    def _countries(self, period: Period) -> list[_Place]:
        raw = self._cached(
            ("countries", period),
            lambda: self._reader.views_by_country(period.start, period.end),
        )
        assert isinstance(raw, dict)  # noqa: S101
        out = []
        for code, n in sorted(raw.items()):
            if n > 0:
                name = UNKNOWN_PLACE if code == UNKNOWN_COUNTRY else COUNTRY_NAMES.get(code)
                out.append(_Place(f"pais:{code}", name or str(code), n))
        return out

    def datasets(
        self,
        sort: Sort,
        limit: int,
        period: Period,
        titles: Mapping[str, tuple[str, str]],
    ) -> MetricsDatasetsOut:
        """Indicadores mais abertos ou mais baixados no período.

        Só entram indicadores com 5 aberturas ou mais e presentes no release ativo.
        """
        self._started()
        rows = self._cached(("kpis", period), lambda: self._reader.kpis(period.start, period.end))
        assert isinstance(rows, list)  # noqa: S101
        items = [
            MetricsDatasetOut(
                kpi_id=r.kpi_id,
                title=titles[r.kpi_id][0],
                theme=titles[r.kpi_id][1],
                views=r.opens,
                downloads=r.downloads,
                api_calls=None,
            )
            for r in rows
            if r.opens >= SUPPRESSION_THRESHOLD
            and r.kpi_id in titles
            and (sort == "views" or r.downloads > 0)
        ]
        items.sort(key=lambda i: (-(i.views if sort == "views" else i.downloads), i.kpi_id))
        return MetricsDatasetsOut(sort=sort, period=period.out(), items=items[:limit])
