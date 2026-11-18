"""Sonda de metadados de tabelas SIDRA pela API ``/values`` (Totais apenas).

Usada pelo panorama (ADR-0010) para conferir, na fonte, o que cada tabela do
Tier 1 oferece antes de configurar a ingestão: variáveis e unidades, períodos,
classificações (nome e categoria Total) e níveis territoriais.

Regras de acesso:

* só consulta tabelas cujo código consta do acervo oficial exportado (nenhuma
  varredura de códigos de tabela ou de classificação);
* usa o ``HttpClient`` da fonte, com o mesmo ritmo, tentativas e respeito a 429;
* consultas sem classificações: a API devolve o Total de cada classificação,
  com o nome da classificação no cabeçalho (os ids ``cNNN`` não vêm na resposta).

Comportamentos observados (2026-11-03 a 2026-11-10): a ordem das dimensões da
resposta segue a da URL (território, variável, período e, depois, as
classificações); nível inexistente na tabela ("Parâmetro N1 (Nível
territorial) incompatível com a tabela") e excesso de valores (50.000)
respondem HTTP 400 com texto simples.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from odb_ingestion.http import HttpClient, HttpError

# Níveis conferidos: Brasil, Grande Região, UF, Região Metropolitana e Município.
# A descrição usa o primeiro que a tabela aceitar (a POF de 1995-1996, por
# exemplo, só tem regiões metropolitanas).
PROBE_LEVELS = ("n1", "n2", "n3", "n7", "n6")
_HTTP_BAD_REQUEST = 400
_INCOMPATIBLE = "incompat"
_LIMIT = "limite"
# Símbolos SIDRA sem valor: não se aplica e não disponível.
_NOT_INFORMATIVE = frozenset({"...", ".."})


class _RefusedError(Exception):
    """HTTP 400 da API, com a mensagem (nível incompatível, excesso de valores...)."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


@dataclass
class ProbeRequest:
    """Uma requisição feita pela sonda (rastreabilidade)."""

    url: str
    status: int | None
    sha256: str | None = None
    size_bytes: int = 0
    error: str | None = None


@dataclass
class TableProbe:
    """Metadados de uma tabela vistos pela API ``/values``."""

    table: str
    status: str = "ok"
    error: str | None = None
    base_level: str | None = None
    variables: list[dict[str, Any]] = field(default_factory=list)
    period_label: str | None = None
    periods: list[str] = field(default_factory=list)
    periods_complete: bool = True
    classifications: list[dict[str, Any]] = field(default_factory=list)
    levels: dict[str, int | None] = field(default_factory=dict)
    requests: list[ProbeRequest] = field(default_factory=list)


def _fetch(http: HttpClient, url: str, log: list[ProbeRequest]) -> list[dict[str, str]]:
    """Linhas da resposta, cabeçalho incluído. HTTP 400 vira ``_RefusedError``."""
    try:
        body = http.get_bytes(url)
    except HttpError as exc:
        log.append(ProbeRequest(url, exc.status, error=str(exc)[:300]))
        if exc.status == _HTTP_BAD_REQUEST:
            raise _RefusedError(str(exc)) from exc
        raise
    log.append(ProbeRequest(url, 200, hashlib.sha256(body).hexdigest(), len(body)))
    payload = json.loads(body)
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        msg = f"{url}: resposta fora do formato esperado"
        raise HttpError(msg, url=url, status=200)
    return payload


def _dims(header: dict[str, str]) -> list[str]:
    """Dimensões ``D1``, ``D2``, ... na ordem da resposta."""
    keys = {k[:-1] for k in header if k.startswith("D") and k.endswith("C")}
    return sorted(keys, key=lambda k: int(k[1:]))


def _territories(rows: list[dict[str, str]]) -> int | None:
    """Territórios com algum valor informativo ("-" é zero; "..." e ".." não contam)."""
    if len(rows) < 2:  # noqa: PLR2004
        return None
    dim = _dims(rows[0])[0]
    found = {r[f"{dim}C"] for r in rows[1:] if r.get("V") not in _NOT_INFORMATIVE}
    return len(found) or None


def _label(header: dict[str, str], dim: str) -> str:
    return header.get(f"{dim}N") or header.get(f"{dim}C", dim).removesuffix(" (Código)")


def _describe(probe: TableProbe, rows: list[dict[str, str]], *, with_periods: bool) -> None:
    header, data = rows[0], rows[1:]
    dims = _dims(header)
    # Território, variável, período e classificações, na ordem da URL.
    var_dim, period_dim, class_dims = dims[1], dims[2], dims[3:]
    variables: dict[str, dict[str, Any]] = {}
    for row in data:
        item = variables.setdefault(
            row[f"{var_dim}C"], {"id": row[f"{var_dim}C"], "name": row[f"{var_dim}N"], "units": []}
        )
        if row.get("MN") and row["MN"] not in item["units"]:
            item["units"].append(row["MN"])
    probe.variables = list(variables.values())
    probe.period_label = _label(header, period_dim)
    if with_periods:
        probe.periods = sorted({row[f"{period_dim}C"] for row in data})
    probe.classifications = []
    for dim in class_dims:
        cats = {(row[f"{dim}C"], row[f"{dim}N"]) for row in data}
        probe.classifications.append(
            {
                "label": _label(header, dim),
                "categories": [{"id": c, "name": n} for c, n in sorted(cats)],
            }
        )


def _describe_at(probe: TableProbe, http: HttpClient, base: str, level: str) -> None:
    """Descreve a tabela num nível aceito; com excesso de valores, pelo último período."""
    try:
        rows = _fetch(http, f"{base}/{level}/all/v/all/p/all", probe.requests)
        if len(rows) < 2:  # noqa: PLR2004
            raise _RefusedError("nenhuma observação")
        _describe(probe, rows, with_periods=True)
        probe.levels[level] = _territories(rows)
    except _RefusedError as exc:
        if _LIMIT not in exc.text:
            raise
        rows = _fetch(http, f"{base}/{level}/all/v/all/p/last%201", probe.requests)
        if len(rows) < 2:  # noqa: PLR2004
            raise _RefusedError("nenhuma observação no último período") from exc
        _describe(probe, rows, with_periods=False)
        probe.levels[level] = _territories(rows)
        first = probe.variables[0]["id"]
        periods = _fetch(http, f"{base}/{level}/all/v/{first}/p/all", probe.requests)
        dim = _dims(periods[0])[2]
        probe.periods = sorted({r[f"{dim}C"] for r in periods[1:]})
        probe.periods_complete = False


def _count_level(probe: TableProbe, http: HttpClient, base: str, level: str) -> int | None:
    """Territórios do nível no último período (None se a tabela não tem o nível)."""
    first = probe.variables[0]["id"]
    try:
        rows = _fetch(http, f"{base}/{level}/all/v/{first}/p/last%201", probe.requests)
    except _RefusedError:
        return None
    return _territories(rows)


def probe_table(http: HttpClient, base_url: str, table: str) -> TableProbe:
    """Variáveis, períodos, classificações (Total) e níveis de uma tabela."""
    base = base_url.rstrip("/") + f"/values/t/{table}"
    probe = TableProbe(table)
    try:
        described: str | None = None
        for level in PROBE_LEVELS:
            try:
                _describe_at(probe, http, base, level)
            except _RefusedError as exc:
                if _INCOMPATIBLE not in exc.text:
                    raise
                probe.levels[level] = None
                continue
            described = level
            break
        if described is None:
            probe.status = "erro"
            probe.error = f"nenhum dos níveis {list(PROBE_LEVELS)} aceito pela tabela"
            return probe
        probe.base_level = described
        for level in PROBE_LEVELS[PROBE_LEVELS.index(described) + 1 :]:
            probe.levels[level] = _count_level(probe, http, base, level)
    except (_RefusedError, HttpError, json.JSONDecodeError, KeyError, IndexError) as exc:
        probe.status = "erro"
        probe.error = f"{type(exc).__name__}: {str(exc)[:300]}"
    return probe
