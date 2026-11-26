"""Confere candidatas contra configuração e dicionários, sem capturar ou ativar dados."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from odb_api.dictionaries import DictionaryCatalog
from odb_ingestion import load_sources
from odb_semantics import load_scope
from odb_semantics.portal import load_portal


def prepare(root: Path) -> dict[str, Any]:
    """Prepara todas as candidatas documentadas; existência de configuração não é aceite."""
    dictionary = DictionaryCatalog(root / "docs/data_catalog/dicionarios-2026-11-26")
    semantic = load_scope(root / "configs/indicators", "demografia")
    portal = load_portal(root / "configs/portal", "demografia")
    sources = load_sources(root / "configs/sources")
    indicators = {item.id: item for item in semantic.indicators}
    kpis = {item.id: item for item in portal.kpis()}
    records = []
    for key, expansion in dictionary.expansions.items():
        entry = dictionary.entry(key)
        indicator = indicators.get(expansion["indicador"])
        kpi = kpis.get(key)
        checks = {
            "configuracao_indicador": indicator is not None,
            "ligacao_kpi": kpi is not None and kpi.indicator == expansion["indicador"],
            "ficha": entry.indicator_id == expansion["indicador"],
            "fontes_configuradas": all(link["dataset"] in sources.datasets for link in entry.links),
            "variaveis_oficiais_identificadas": all(
                bool(link["variavel_oficial"]) for link in entry.links
            ),
        }
        if indicator:
            checks["fato_configurado"] = any(fact.id == indicator.fact for fact in semantic.facts)
        records.append(
            {
                **expansion,
                "checks": checks,
                "estado_preparacao": "configuracao_conferida"
                if all(checks.values())
                else "pendencias_configuracao",
                "tabelas_variaveis": [
                    {"tabela": link["tabela"], "variavel": link["variavel"]} for link in entry.links
                ],
                "metodos_documentais": entry.document["metodos"],
                "lacunas": entry.document["lacunas"],
                "publicavel": False,
                "proximo_passo": (
                    "Resolver precisão e linhagem; candidata reprovada permanece bloqueada."
                    if expansion["lote"] == "N5"
                    else "Reconciliar a candidata exata, completar validações e obter aceite."
                ),
            }
        )
    return {
        "schema_version": "odb-preparacao/1.0.0",
        "dictionary_version": dictionary.version,
        "natureza": "conferencia_estatica_sem_ativacao",
        "total": len(records),
        "por_lote": dict(Counter(item["lote"] for item in records)),
        "indicadores": records,
    }


def main() -> None:
    """Grava relatório novo no destino explícito, preservando evidências anteriores."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    content = prepare(args.root)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(content, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
