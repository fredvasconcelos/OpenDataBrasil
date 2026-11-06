"""Contrato da API (§18.3, §24.1): o OpenAPI gerado é igual ao de referência.

Uma mudança de rota, parâmetro ou modelo falha este teste. Se for intencional,
regenere a referência e os tipos do portal:

    uv run python -m odb_api.app tests/contracts/openapi.json
    (apps/portal) npm run gen:api

Mudanças incompatíveis (remover campo, rota ou parâmetro) exigem aprovação (§28.5).
"""

import json
from pathlib import Path

from odb_api.app import create_app

REFERENCE = Path(__file__).parent / "openapi.json"


def test_openapi_matches_reference() -> None:
    current = json.loads(json.dumps(create_app(None).openapi(), ensure_ascii=False))
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    assert set(current["paths"]) == set(reference["paths"])
    assert current == reference
