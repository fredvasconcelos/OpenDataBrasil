"""Diagnostica amostras locais Elmar/PB; não ingere, modela nem publica dados.

Executar com Python -I. Lê resposta e manifesto no mesmo diretório, verifica
integridade e descreve somente o recorte recebido, sem inferir cobertura do ente.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, parse_qs, urlsplit

MUNICIPAL_AMOUNTS = (
    "dotacaoInicial",
    "suplementadoNoMes",
    "anuladoNoMes",
    "dotacaoAtualizada",
    "empenhado",
    "liquidadoNoMes",
    "pagoNoMes",
    "saldo",
    "saldoAPagar",
)
STATE_AMOUNTS = (
    "orcamentoInicial",
    "orcamentoAtualizado",
    "valorEmpenhado",
    "valorLiquidado",
    "valorPago",
    "saldoAPagar",
)
MAX_BYTES = 5 * 1024**2
HTTP_OK = 200
MONTHS_PER_YEAR = 12
MAX_PAGE_SIZE = 1000


def _reject_constant(value: str) -> None:
    raise ValueError(f"Constante JSON inválida: {value}")


def _load(raw: bytes) -> Any:
    return json.loads(raw, parse_float=Decimal, parse_constant=_reject_constant)


def _one(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    if len(values) != 1 or not values[0]:
        raise ValueError(f"Parâmetro ausente ou repetido: {key}")
    return values[0]


def _amounts(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for field in fields:
        values = []
        missing = 0
        for row in rows:
            value = row[field]  # coluna ausente é erro; null é ausência explícita
            if value is None:
                missing += 1
                continue
            if isinstance(value, bool) or not isinstance(value, int | Decimal):
                raise ValueError(f"Valor monetário inválido: {field}")
            decimal = Decimal(value)
            if not decimal.is_finite() or decimal != decimal.quantize(Decimal("0.01")):
                raise ValueError(f"Precisão monetária inválida: {field}")
            values.append(decimal)
        result[field] = {
            "presentes": len(values),
            "ausentes": missing,
            "zeros": sum(v == 0 for v in values),
            "negativos": sum(v < 0 for v in values),
            "soma_das_linhas_recebidas": str(sum(values, Decimal(0))) if values else None,
        }
    return result


def _elmar_context(
    url: SplitResult,
    query: dict[str, list[str]],
    rows: list[dict[str, Any]],
) -> tuple[int, int, str, dict[str, Any], tuple[str, ...]]:
    """Confere a entidade isolada e a competência retornada pelo município."""
    entity = url.path.removeprefix("/api/v2/").partition("/")[0]
    if url.netloc != "transparencia-api.elmartecnologia.com.br" or url.path != (
        f"/api/v2/{entity}/contab/despesas/fixada"
    ):
        raise ValueError("Endpoint municipal incompatível com o descritor")
    period = _one(query, "competencia")
    year = int(_one(query, "exercicio"))
    month, period_year = (int(v) for v in period.split("/"))
    if period_year != year or not 1 <= month <= MONTHS_PER_YEAR:
        raise ValueError("Competência municipal inválida")
    if _one(query, "exibeConsolidado") != "false":
        raise ValueError("Consolidação de entidades fora do piloto")
    if any(r["competencia"] != period or r["ecode"] != entity for r in rows):
        raise ValueError("Competência ou entidade diverge da consulta")
    if len({r["sequencia"] for r in rows}) != len(rows):
        raise ValueError("Sequência municipal repetida no retorno")
    fields = MUNICIPAL_AMOUNTS
    coverage: dict[str, Any] = {"completude": "não demonstrada; sem total/paginação"}
    mode = "semântica temporal por campo pendente"
    return year, month, mode, coverage, fields


def _pb_context(
    url: SplitResult,
    query: dict[str, list[str]],
    rows: list[dict[str, Any]],
    payload: dict[str, Any],
) -> tuple[int, int, str, dict[str, Any], tuple[str, ...]]:
    """Confere modalidade temporal e paginação estadual explicitamente solicitadas."""
    if url.netloc != "api.dados.pb.gov.br" or url.path != (
        "/api/v1/despesas/execucao_orcamentaria"
    ):
        raise ValueError("Endpoint estadual incompatível com o descritor")
    year, month = int(_one(query, "ano")), int(_one(query, "mes"))
    mode = _one(query, "acumular")
    if not 1 <= month <= MONTHS_PER_YEAR or mode not in {"Até o mês", "No mês"}:
        raise ValueError("Referência temporal estadual inválida")
    if any(r["ano"] != year or r["mes"] != month for r in rows):
        raise ValueError("Período estadual diverge da consulta")
    page = payload["paginacao"]
    total, size = page["total"], page["itens_por_pagina"]
    number = page["pagina"]
    if not all(type(v) is int for v in (total, size, number, page["total_paginas"])):
        raise ValueError("Paginação deve usar inteiros")
    if total < 0 or not 1 <= size <= MAX_PAGE_SIZE or number < 1:
        raise ValueError("Limites de paginação inválidos")
    expected = max(0, min(size, total - (number - 1) * size))
    if (
        size != int(_one(query, "per_page"))
        or number != int(_one(query, "page"))
        or len(rows) != expected
        or page["total_paginas"] != math.ceil(total / size)
    ):
        raise ValueError("Paginação não reconcilia com o retorno")
    coverage = {**page, "recorte_completo": number == 1 and total == len(rows)}
    fields = STATE_AMOUNTS
    return year, month, mode, coverage, fields


def diagnose(manifest_path: Path, source: str) -> dict[str, Any]:
    """Confere integridade e recorte; falha fechada diante de período ou forma incompatível."""
    manifest = json.loads(manifest_path.read_bytes())
    response = manifest_path.parent / "resposta"
    if response.stat().st_size > MAX_BYTES:
        raise ValueError("Resposta excedeu 5 MiB")
    raw = response.read_bytes()
    if (
        manifest.get("status") != HTTP_OK
        or manifest.get("bytes") != len(raw)
        or manifest.get("sha256") != hashlib.sha256(raw).hexdigest()
    ):
        raise ValueError("Integridade ou status HTTP incompatível com o manifesto")
    url = urlsplit(manifest["url"])
    if url.scheme != "https":
        raise ValueError("A fonte deve usar HTTPS")
    if manifest.get("url_final") != manifest["url"]:
        raise ValueError("Redirecionamento precisa de revisão do descritor")
    query = parse_qs(url.query)
    payload = _load(raw)
    key = "data" if source == "elmar" else "dados"
    rows = payload[key]
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Amostra deve conter uma lista de registros")
    # Duplicata exata no mesmo retorno é diagnóstico bloqueante, não deduplicação.
    signatures = [json.dumps(r, sort_keys=True, default=str) for r in rows]
    if len(signatures) != len(set(signatures)):
        raise ValueError("Registro duplicado no retorno")
    if source == "elmar":
        year, month, mode, coverage, fields = _elmar_context(url, query, rows)
    elif source == "pb":
        year, month, mode, coverage, fields = _pb_context(url, query, rows, payload)
    else:
        raise ValueError("Fonte fora do piloto")
    return {
        "fonte": source,
        "url": manifest["url"],
        "sha256": manifest["sha256"],
        "referencia": f"{year:04d}-{month:02d}",
        "modalidade_temporal": mode,
        "linhas": len(rows),
        "cobertura": coverage,
        "campos": _amounts(rows, fields),
        "publicacao": "não autorizada pelo diagnóstico; contrato e aceite pendentes",
    }


def main() -> None:
    """Grava diagnóstico separado dos originais, sem sobrescrever arquivos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("elmar", "pb"), required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.manifest, args.source)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
