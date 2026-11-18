#!/usr/bin/env python3
"""Recorta o Prometheus da Vitrine por patamar de uma escada do k6 (``escada.js``).

Uso, com o túnel SSH do runbook da Vitrine expondo o Prometheus em ``localhost:9092``::

    ssh -f -N -L 9092:localhost:9091 "$ODB_VITRINE_HOST"
    python3 -I tests/performance/k6/patamares.py --t0 <epoch do início da escada> \\
        --alvos 4,8,12,16,25,35,50,70,100,150,200 --plato 75 --saida patamares.json

Cada degrau do ``escada.js`` tem ``--rampa`` segundos de subida e ``--plato`` segundos de
platô; mede-se do primeiro terço ao fim do platô, com amostras a cada 15 s. Os contêineres
são somados por serviço (``odb-vitrine-portal-1``, ``-2``...), então a análise vale também
com réplicas. O histograma do Caddy termina em 10 s: um p95 de 10000 ms quer dizer "10 s ou
mais" (saturado); o valor real vem do resumo do k6.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.parse
import urllib.request


def _ctr(servico: str) -> str:
    return f'name=~"odb-vitrine-{servico}-[0-9]+"'


def _p(q: float, metrica: str) -> str:
    return f"1000 * histogram_quantile({q}, sum by (le) (rate({metrica}_bucket[1m])))"


def _cpu(servico: str) -> str:
    return f"100 * sum(rate(container_cpu_usage_seconds_total{{{_ctr(servico)}}}[1m]))"


def _estrangulado(servico: str) -> str:
    return (
        f"100 * sum(rate(container_cpu_cfs_throttled_periods_total{{{_ctr(servico)}}}[1m]))"
        f" / sum(rate(container_cpu_cfs_periods_total{{{_ctr(servico)}}}[1m]))"
    )


CONSULTAS = {
    "rps": "sum(rate(caddy_http_requests_total[1m]))",
    "p95_e2e_ms": _p(0.95, "caddy_http_request_duration_seconds"),
    "p99_e2e_ms": _p(0.99, "caddy_http_request_duration_seconds"),
    "p95_api_ms": _p(0.95, "http_server_request_duration_seconds"),
    "p95_duckdb_ms": _p(0.95, "odb_duckdb_query_duration_seconds"),
    "5xx_por_s": 'sum(rate(caddy_http_requests_total{code=~"5.."}[1m])) or vector(0)',
    "em_voo": "sum(caddy_http_requests_in_flight)",
    "cpu_api_pct": _cpu("api"),
    "cpu_portal_pct": _cpu("portal"),
    "cpu_caddy_pct": _cpu("caddy"),
    "portal_estrangulado_pct": _estrangulado("portal"),
    "api_estrangulada_pct": _estrangulado("api"),
    "mem_api_mib": f"sum(container_memory_working_set_bytes{{{_ctr('api')}}}) / 1048576",
    "load1": "node_load1",
    "temp_c": "max(node_hwmon_temp_celsius)",
}


def _valor(prom: str, expr: str, instante: float) -> float:
    url = f"{prom}/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": instante})
    with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310 - URL do túnel local
        resultado = json.load(resp)["data"]["result"]
    return float(resultado[0]["value"][1]) if resultado else math.nan


def _media(prom: str, expr: str, inicio: float, fim: float) -> float:
    valores = []
    t = inicio
    while t <= fim:
        v = _valor(prom, expr, t)
        if not math.isnan(v):
            valores.append(v)
        t += 15
    return sum(valores) / len(valores) if valores else math.nan


def main() -> None:
    """Imprime uma linha por patamar e grava o JSON."""
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--prom", default="http://localhost:9092")
    args.add_argument("--t0", type=int, required=True, help="epoch do início da escada")
    args.add_argument("--alvos", required=True, help="usuários por degrau, ex.: 4,8,12")
    args.add_argument("--rampa", type=int, default=30)
    args.add_argument("--plato", type=int, default=120)
    args.add_argument("--saida", default="patamares.json")
    a = args.parse_args()

    linhas = []
    cursor = a.t0
    print("usuarios\t" + "\t".join(CONSULTAS))
    for alvo in (int(x) for x in a.alvos.split(",")):
        cursor += a.rampa
        inicio, fim = cursor + a.plato // 3, cursor + a.plato
        cursor += a.plato
        if inicio > time.time():
            break  # a escada não chegou aqui (ou abortou)
        linha: dict[str, float] = {"usuarios": alvo}
        for nome, expr in CONSULTAS.items():
            linha[nome] = round(_media(a.prom, expr, inicio, fim), 2)
        linhas.append(linha)
        print("\t".join(str(linha[k]) for k in ("usuarios", *CONSULTAS)), flush=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(linhas, f, indent=1)


if __name__ == "__main__":
    main()
