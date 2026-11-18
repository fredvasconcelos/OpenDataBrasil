"""Confere se a Vitrine responde igual à Fábrica (plano R-V, etapa V2).

Monta requisições reais a partir da navegação do portal (mapas, séries, detalhes, tabelas)
e compara o status e o SHA-256 do corpo nos dois lados, pelo proxy /odb-api do portal.

Uso:
    python3 tests/vitrine/compare_responses.py \
        --fabrica http://localhost:3000 --vitrine https://vitrine.example [--n 50]
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from typing import cast
from urllib.parse import urlencode


def abrir(url: str) -> http.client.HTTPResponse:
    """Abre só URLs http(s) (as bases vêm da linha de comando)."""
    if not url.startswith(("http://", "https://")):
        msg = f"URL não http(s): {url}"
        raise ValueError(msg)
    return cast(http.client.HTTPResponse, urllib.request.urlopen(url, timeout=60))  # noqa: S310 - esquema conferido acima


def buscar(base: str, caminho: str) -> tuple[int, str, float]:
    """Status, SHA-256 do corpo e segundos da requisição."""
    inicio = time.perf_counter()
    try:
        with abrir(f"{base}/odb-api/{caminho}") as r:
            corpo, status = r.read(), r.status
    except urllib.error.HTTPError as erro:
        corpo, status = erro.read(), erro.code
    return status, hashlib.sha256(corpo).hexdigest(), time.perf_counter() - inicio


def requisicoes(base: str, n: int) -> list[str]:
    """Requisições variadas: um KPI por tema, depois mais KPIs até chegar a n."""
    with abrir(f"{base}/odb-api/portal/navigation") as r:
        nav = json.load(r)
    kpis = [k for t in nav["themes"] for s in t["subthemes"] for k in s["kpis"]]
    por_tema = {k["theme_id"]: k for k in reversed(kpis)}
    ordem = list(por_tema.values()) + [k for k in kpis if k not in por_tema.values()]
    saida = ["release", "portal/navigation", "geometries/uf"]
    for kpi in ordem:
        kid, periodo = kpi["kpi_id"], (kpi["periods"] or [None])[-1]
        q = {"period": periodo} if periodo else {}
        nivel = "uf" if "uf" in kpi["map_levels"] else (kpi["map_levels"] or ["brasil"])[0]
        saida.append(f"kpis/{kid}/map?{urlencode({'level': nivel, **q})}")
        saida.append(f"kpis/{kid}/series?{urlencode({'geography': 'brasil:1'})}")
        if kpi["dimensions"] and "uf" in kpi["levels"]:
            dims = kpi["dimensions"][0]["classification_id"]
            saida.append(
                f"kpis/{kid}/detail?{urlencode({'geography': 'uf:35', 'dimensions': dims, **q})}"
            )
        if len(saida) >= n:
            break
    return saida[:n]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fabrica", default="http://localhost:3000")
    p.add_argument("--vitrine", required=True)
    p.add_argument("--n", type=int, default=50)
    args = p.parse_args()

    lista = requisicoes(args.fabrica, args.n)
    diferentes = 0
    for caminho in lista:
        sf, hf, tf = buscar(args.fabrica, caminho)
        sv, hv, tv = buscar(args.vitrine, caminho)
        igual = (sf, hf) == (sv, hv)
        diferentes += not igual
        marca = "ok " if igual else "DIF"
        print(f"{marca} {sf} {sv} fábrica {tf:5.2f}s vitrine {tv:5.2f}s  {caminho}")
    print(f"\n{len(lista) - diferentes}/{len(lista)} respostas idênticas")
    return 1 if diferentes else 0


if __name__ == "__main__":
    sys.exit(main())
