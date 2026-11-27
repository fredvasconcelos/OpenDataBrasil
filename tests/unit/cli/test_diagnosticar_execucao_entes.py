"""Proteções do piloto Elmar/PB com valores sintéticos, sem acesso à rede."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[3] / "infrastructure/scripts/diagnosticar_execucao_entes.py"
SPEC = importlib.util.spec_from_file_location("diagnostico_entes", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample(
    tmp_path: Path,
    source: str = "elmar",
    *,
    amount: object = -3.15,
    period: str = "07/2026",
    total: int = 1,
) -> Path:
    fields = MODULE.MUNICIPAL_AMOUNTS if source == "elmar" else MODULE.STATE_AMOUNTS
    row: dict[str, Any] = dict.fromkeys(fields, 0)
    row[fields[0]] = amount
    if source == "elmar":
        row.update(competencia=period, ecode="201082", sequencia=1)
        url = (
            "https://transparencia-api.elmartecnologia.com.br/api/v2/201082/contab/despesas/"
            "fixada?competencia=07%2F2026&exercicio=2026&exibeConsolidado=false"
        )
        payload: dict[str, Any] = {"data": [row]}
    else:
        row.update(ano=2026, mes=7)
        url = (
            "https://api.dados.pb.gov.br/api/v1/despesas/execucao_orcamentaria?"
            "ano=2026&mes=07&acumular=At%C3%A9%20o%20m%C3%AAs&page=1&per_page=1"
        )
        payload = {
            "dados": [row],
            "paginacao": {
                "total": total,
                "pagina": 1,
                "itens_por_pagina": 1,
                "total_paginas": total,
            },
        }
    raw = json.dumps(payload).encode()
    (tmp_path / "resposta").write_bytes(raw)
    path = tmp_path / "manifesto.json"
    path.write_text(
        json.dumps(
            {
                "url": url,
                "url_final": url,
                "status": 200,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    )
    return path


def test_preserva_negativo_zero_e_nao_certifica_cobertura_municipal(tmp_path: Path) -> None:
    path = sample(tmp_path)
    result = MODULE.diagnose(path, "elmar")
    assert result["campos"]["dotacaoInicial"]["soma_das_linhas_recebidas"] == "-3.15"
    assert result["campos"]["dotacaoInicial"]["negativos"] == 1
    assert result["campos"]["pagoNoMes"]["zeros"] == 1
    assert "não demonstrada" in result["cobertura"]["completude"]
    assert MODULE.diagnose(path, "elmar") == result


def test_ausencia_explicita_nao_vira_zero(tmp_path: Path) -> None:
    result = MODULE.diagnose(sample(tmp_path, amount=None), "elmar")
    values = result["campos"]["dotacaoInicial"]
    assert values["ausentes"] == 1
    assert values["zeros"] == 0
    assert values["soma_das_linhas_recebidas"] is None


@pytest.mark.parametrize("amount", [True, "3.15", 0.001, float("nan"), float("inf")])
def test_rejeita_valor_invalido_ou_arredondamento(tmp_path: Path, amount: object) -> None:
    with pytest.raises(ValueError, match="inválid"):
        MODULE.diagnose(sample(tmp_path, amount=amount), "elmar")


def test_arquivo_alterado_falha_por_hash(tmp_path: Path) -> None:
    path = sample(tmp_path)
    (tmp_path / "resposta").write_bytes(b'{"data": []}')
    with pytest.raises(ValueError, match="Integridade"):
        MODULE.diagnose(path, "elmar")


def test_periodo_ignorado_pela_fonte_falha(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Competência ou entidade"):
        MODULE.diagnose(sample(tmp_path, period="11/2026"), "elmar")


@pytest.mark.parametrize(("total", "complete"), [(1, True), (334, False)])
def test_distingue_pagina_estadual_de_recorte_completo(
    tmp_path: Path,
    total: int,
    complete: bool,
) -> None:
    result = MODULE.diagnose(sample(tmp_path, "pb", total=total), "pb")
    assert result["cobertura"]["recorte_completo"] is complete
    assert result["modalidade_temporal"] == "Até o mês"


def test_total_paginas_inconsistente_bloqueia(tmp_path: Path) -> None:
    path = sample(tmp_path, "pb", total=334)
    raw = json.loads((tmp_path / "resposta").read_bytes())
    raw["paginacao"]["total_paginas"] = 1
    data = json.dumps(raw).encode()
    (tmp_path / "resposta").write_bytes(data)
    manifest = json.loads(path.read_bytes())
    manifest.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Paginação"):
        MODULE.diagnose(path, "pb")
