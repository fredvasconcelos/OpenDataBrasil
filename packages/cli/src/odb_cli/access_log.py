"""Classificação das linhas do log de acesso do Caddy (ADR-0027).

Cada linha é um JSON que o Caddy grava **já sem** IP, porta, cabeçalhos da requisição e
da resposta (filtro em ``infrastructure/vitrine/Caddyfile``). Só chegam aqui os campos
acrescentados por ``log_append``:

- ``country`` e ``region``: ``CF-IPCountry`` e ``cf-region-code`` da Cloudflare;
- ``referer``, ``ua``: origem e *user agent*, usados aqui e descartados (só o domínio de
  origem e a contagem entram no banco);
- ``rsc``, ``prefetch``, ``purpose``: cabeçalhos do Next.js e do navegador que separam a
  navegação real do *prefetch*;
- ``export_kpi``, ``export_format``: cabeçalhos da resposta da exportação.

Regras de contagem:

- **Visualização** (``page_view``): ``GET`` de página com status 200, sem *prefetch*.
  Uma requisição RSC (navegação do Next.js sem recarregar) só conta quando muda de rota:
  trocar filtros no painel faz ``router.replace`` na mesma rota e não é nova página.
- **Abertura de indicador** (``kpi_open``): ``/dashboard`` com ``?kpi=`` diferente do
  ``kpi`` da página anterior (ou vindo de outra página).
- **Download**: ``POST /odb-api/exports`` com status 200; indicador e formato vêm dos
  cabeçalhos ``X-ODB-KPI`` e ``X-ODB-Format`` que a API devolve.
- Robôs (pelo *user agent*) não contam. Local desconhecido vira ``ZZ`` / UF ``0``,
  nunca um lugar arbitrário.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from odb_catalog.access_metrics import UF_CODES, UNKNOWN_COUNTRY, UNKNOWN_UF, AccessKey

TZ = ZoneInfo("America/Sao_Paulo")
EXPORT_PATH = "/odb-api/exports"
DASHBOARD = "/dashboard"
FORMATS = frozenset({"csv", "xlsx", "parquet", "json"})
_OK = 200
_MAX_ROUTE = 200
_MAX_DOMAIN = 253
_KPI = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_DOMAIN = re.compile(r"^[a-z0-9.-]+$")
# Prefixos que não são páginas: estáticos do Next.js, proxy da API e o tique de rotação.
_NOT_PAGES = ("/_next/", "/odb-api/", "/_odb/")
# Robôs, prévias de link e clientes de linha de comando. Sem user agent também é robô.
_ROBOT = re.compile(
    r"bot|crawl|spider|slurp|scrap|preview|monitor|uptime|lighthouse|headless|pingdom|"
    r"curl|wget|python|httpx|aiohttp|go-http|java/|okhttp|libwww|node-fetch|axios|"
    r"facebookexternalhit|whatsapp|telegram|discord|slack|embedly|"
    r"^mozilla/5\.0$",
    re.IGNORECASE,
)


def is_robot(user_agent: str) -> bool:
    """Robô, prévia de link ou cliente automático (inclui *user agent* vazio)."""
    return not user_agent.strip() or bool(_ROBOT.search(user_agent))


def location(country: str, region: str) -> tuple[str, int]:
    """País ISO 3166-1 alfa-2 e código IBGE da UF.

    ``cf-region-code`` vem como a parte da subdivisão ISO 3166-2 (``SP``); aceitamos também
    ``BR-SP``. País fora do padrão, ``XX`` (desconhecido) e ``T1`` (Tor) viram ``ZZ``.
    """
    c = country.strip().upper()
    if not _COUNTRY.match(c) or c == "XX":
        return UNKNOWN_COUNTRY, UNKNOWN_UF
    if c != "BR":
        return c, UNKNOWN_UF
    r = region.strip().upper().removeprefix("BR-")
    return c, UF_CODES.get(r, UNKNOWN_UF)


def day_of(ts: float) -> date:
    """Dia do acesso no fuso de Brasília."""
    return datetime.fromtimestamp(ts, tz=TZ).date()


def _route(path: str) -> str:
    route = path.rstrip("/") or "/"
    return route[:_MAX_ROUTE]


def _is_page(path: str) -> bool:
    if path.startswith(_NOT_PAGES):
        return False
    # Arquivos de public/ (ícones, bandeiras, robots.txt) têm extensão; páginas não.
    return "." not in path.rsplit("/", 1)[-1]


def _kpi_of(query: str) -> str:
    values = parse_qs(query).get("kpi", [])
    kpi = values[0] if values else ""
    return kpi if _KPI.match(kpi) else ""


def _hostname(url: str) -> str:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "") if parts.scheme in {"http", "https"} else ""
    except ValueError:
        return ""
    return host if len(host) <= _MAX_DOMAIN and _DOMAIN.match(host) else ""


def _download(day: date, country: str, uf: int, text: dict[str, str]) -> list[AccessKey]:
    fmt = text.get("export_format", "").lower()
    if fmt not in FORMATS:
        return []
    kpi = text.get("export_kpi", "")
    return [
        AccessKey(
            day,
            "download",
            country,
            uf,
            route=EXPORT_PATH,
            kpi_id=kpi if _KPI.match(kpi) else "",
            format=fmt,
        )
    ]


def classify(entry: dict[str, object]) -> list[AccessKey]:
    """Contagens geradas por uma linha do log (nenhuma, uma ou duas)."""
    request = entry.get("request")
    ts = entry.get("ts")
    if not isinstance(request, dict) or not isinstance(ts, int | float):
        return []
    text = {k: str(v) if v is not None else "" for k, v in entry.items() if k != "request"}
    if is_robot(text.get("ua", "")):
        return []
    method = str(request.get("method", ""))
    uri = urlsplit(str(request.get("uri", "")))
    status = entry.get("status")
    day = day_of(float(ts))
    country, uf = location(text.get("country", ""), text.get("region", ""))

    if method == "POST" and uri.path == EXPORT_PATH and status == _OK:
        return _download(day, country, uf, text)
    if method != "GET" or status != _OK or not _is_page(uri.path):
        return []
    if text.get("prefetch") or "prefetch" in text.get("purpose", "").lower():
        return []

    route = _route(uri.path)
    host = (str(request.get("host", "")).split(":", 1)[0]).lower()
    referer = text.get("referer", "")
    ref_host = _hostname(referer)
    same_site = bool(ref_host) and ref_host == host
    ref = urlsplit(referer) if same_site else None
    ref_route = _route(ref.path) if ref else ""
    rsc = bool(text.get("rsc"))

    out: list[AccessKey] = []
    if not rsc or ref_route != route:
        origin = "" if same_site else ref_host
        out.append(AccessKey(day, "page_view", country, uf, route=route, referrer_domain=origin))
    if route == DASHBOARD:
        kpi = _kpi_of(uri.query)
        previous = _kpi_of(ref.query) if ref and ref_route == DASHBOARD else ""
        if kpi and (not rsc or kpi != previous):
            out.append(AccessKey(day, "kpi_open", country, uf, route=route, kpi_id=kpi))
    return out


def aggregate(lines: Iterable[bytes | str]) -> tuple[Counter[AccessKey], int, int]:
    """Somas de um trecho do log: (contagens, linhas lidas, linhas inválidas)."""
    counts: Counter[AccessKey] = Counter()
    total = invalid = 0
    for raw in lines:
        if not raw.strip():
            continue
        total += 1
        try:
            entry = json.loads(raw)
        except ValueError:
            invalid += 1
            continue
        if not isinstance(entry, dict):
            invalid += 1
            continue
        counts.update(classify(entry))
    return counts, total, invalid
