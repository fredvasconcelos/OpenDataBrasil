"""Contrato OpenAPI como o atacante o vê: só as rotas que o proxy /odb-api do portal deixa
passar, com o servidor apontando para a Vitrine (plano R-V, etapa V6).

Uso: python3 tests/security/openapi_proxy.py <base> <saída.json>
     (ex.: https://vitrine.example /tmp/openapi-vitrine.json)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Mesma lista do proxy (apps/portal/src/app/odb-api/[...path]/route.ts).
PERMITIDOS = {
    "portal", "kpis", "geometries", "geographies", "indicators", "datasets", "sources",
    "release", "exports",
}  # fmt: skip
PREFIXO = "/api/v1/"


def main() -> None:
    base, saida = sys.argv[1], Path(sys.argv[2])
    contrato = Path(__file__).parents[1] / "contracts" / "openapi.json"
    spec = json.loads(contrato.read_text(encoding="utf-8"))
    caminhos = {}
    for caminho, ops in spec["paths"].items():
        if not caminho.startswith(PREFIXO):
            continue
        resto = caminho.removeprefix(PREFIXO)
        if resto.split("/", 1)[0] in PERMITIDOS:
            caminhos["/" + resto] = ops
    spec["paths"] = caminhos
    spec["servers"] = [{"url": base.rstrip("/") + "/odb-api"}]
    saida.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    print(f"{len(caminhos)} rotas expostas pelo proxy -> {saida}")


if __name__ == "__main__":
    main()
