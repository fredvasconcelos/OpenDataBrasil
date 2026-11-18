"""Compila medidas agropecuárias com calendário e unidade homogêneos."""

from __future__ import annotations

import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

from odb_cli.panorama_gen import (
    PERIOD_TYPES,
    Generated,
    _detail_of,
    _register,
    official_notes,
    render_indicators,
    render_portal,
    render_sources,
)
from odb_cli.panorama_medidas import available_periods
from odb_ingestion.connectors.sidra import SidraParams
from odb_semantics import PanoramaKpi, load_panorama

HEADER = "# Gerado por `odb panorama gerar-agro`. Edite configs/catalog/medidas-agro.toml.\n"


def _cohorts(
    descriptor: dict[str, Any], item: dict[str, Any], cuts: dict[str, str]
) -> dict[tuple[str, ...], list[str]]:
    """Cruza a disponibilidade nativa de produto, variável e unidade escolhida."""
    measure = next(v for v in descriptor["Variaveis"] if str(v["Id"]) == item["variable"])
    classification = descriptor["Classificacoes"][0]
    all_periods = available_periods(descriptor, measure.get("PeriodoDisponibilidadeExcecao", ""))
    currency = re.search(rf"{re.escape(item['unit'])} \[([^\]]+)\]", measure["UnidadeMedida"])
    if currency:
        allowed_money = available_periods(descriptor, currency[1])
        all_periods = [p for p in all_periods if p in allowed_money]
    allowed = {str(c["Id"]) for c in classification["Categorias"]}
    chosen = set(item.get("categories", allowed)) - set(item.get("exclude_categories", []))
    if not chosen or chosen - allowed:
        raise ValueError(f"{item['id']}: produtos fora do descritor: {chosen - allowed}")
    groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    if item["variable"] in ("214", "112") and "0" in chosen:
        raise ValueError(f"{item['id']}: a nota 7 da 5457 não permite Total nesta medida")
    for category in classification["Categorias"]:
        code = str(category["Id"])
        if code not in chosen:
            continue
        periods = available_periods(descriptor, category.get("PeriodoDisponibilidadeExcecao", ""))
        first = max(item["first_period"], cuts.get(code, item["first_period"]))
        selected = tuple(p for p in periods if p in all_periods and p >= first)
        if selected:
            groups[selected].append(code)
    return groups


def generate_agro(root: Path) -> Generated:
    """Agrupa produtos por calendários oficiais, sem baixar moedas ou unidades excluídas."""
    spec = tomllib.loads((root / "catalog/medidas-agro.toml").read_text())
    parents = {k.id: (t, s, k) for t, s, k in load_panorama(root / "catalog/panorama.toml").items()}
    generated = Generated()
    for item in spec["measures"]:
        table, variable = item["table"], item["variable"]
        descriptor = json.loads((root / f"catalog/descritores/t{table}.json").read_text())
        measure = next(v for v in descriptor["Variaveis"] if str(v["Id"]) == variable)
        classification = descriptor["Classificacoes"][0]
        cid = f"c{classification['Id']}"
        theme, subtheme, parent = parents[item["parent"]]
        if parent.tabela != table:
            raise ValueError(f"{item['id']}: tabela difere da fonte do KPI de origem")
        cuts = spec.get("category_cuts", {}) if variable in ("214", "112") else {}
        groups = _cohorts(descriptor, item, cuts)
        period_type, frequency = PERIOD_TYPES[descriptor["TipoPeriodo"]]
        source_suffix = item["suffix"].replace("_", "-")
        series_id = f"ibge-agro-{table}-{variable}-{source_suffix}"
        levels = [
            f"n{n['Id']}" for n in descriptor["NiveisTerritoriais"] if n["Id"] in (1, 2, 3, 6)
        ]
        count = sum(
            n["QuantidadeUnidadesAtivas"]
            for n in descriptor["NiveisTerritoriais"]
            if f"n{n['Id']}" in levels
        )
        for order, (periods, categories) in enumerate(sorted(groups.items()), 1):
            per_period = (count + 40) * (
                min(len(categories), 8) if "n6" in levels else len(categories)
            )
            maximum = per_period * frequency
            params = {
                "table": table,
                "variables": [variable],
                "territorial_levels": levels,
                "periods": list(periods),
                "period_type": period_type,
                "group_periods_by_year": period_type != "ano",
                "classifications": {cid: ",".join(categories)},
                "category_chunk": 8,
                "estimated_values_per_period": maximum,
                "max_rows": maximum,
                "min_rows": 1,
                "refresh_recent_periods": 1,
            }
            SidraParams.model_validate(params)
            generated.datasets.append(
                {
                    "id": f"ibge-medida-t{table}-v{variable}-{source_suffix}-g{order}",
                    "source": "ibge-sidra",
                    "official_id": table,
                    "title": item["label"],
                    "description": item["note"],
                    "license": "ibge-reuso-com-citacao",
                    "access_classification": "public_conditional",
                    "periodicity": {"ano": "anual", "mes": "mensal", "trimestre": "trimestral"}[
                        period_type
                    ],
                    "reference_url": f"https://sidra.ibge.gov.br/tabela/{table}",
                    "params": params,
                    "silver": {
                        "transformer": "sidra_observation",
                        "territorial_reference": "ibge-dtb",
                        "panorama_support": True,
                        "series": series_id,
                        "series_order": order,
                    },
                }
            )
        detail, reason = _detail_of(classification, {})
        if detail is None:
            raise ValueError(f"{item['id']}: {reason}")
        detail.cid = f"c{classification['Id']}ag"
        reason = _register(generated, detail, table, {})
        if reason:
            raise ValueError(reason)
        entry = generated.classifications[detail.cid]
        entry["datasets"] = [d for d in entry["datasets"] if d != f"ibge-sidra-{table}"]
        if series_id not in entry["datasets"]:
            entry["datasets"].append(series_id)
        fact_id = f"fact_agro_{table}_{variable}_{item['suffix']}"
        rules: dict[str, Any] = {}
        if item.get("documented_unit"):
            rules["unit"] = item["unit"]
        generated.facts.append(
            {
                "id": fact_id,
                "dataset": series_id,
                "grain": "território x "
                + {"ano": "ano", "mes": "mês", "trimestre": "trimestre"}[period_type]
                + " x produto",
                "description": item["label"],
                "classifications": {detail.cid: f"{detail.cid}_category_key"},
                **({"table_rules": {table: rules}} if rules else {}),
            }
        )
        generated.indicators.append(
            {
                "id": item["id"],
                "name": item["label"],
                "description": measure["Nome"],
                "dataset": series_id,
                "variable": variable,
                "fact": fact_id,
                "column": "valor",
                "unit": item["unit"],
                "additivity": "additive"
                if measure.get("PermiteSomaUnidadesTerritoriais")
                else "non_additive",
                "concept": item["id"],
                "path": [theme.label, subtheme.label],
                "first_period": item["first_period"],
                "caveats": [item["note"], *official_notes(descriptor)],
            }
        )
        if item["publish"]:
            if parents[item["id"]][2].kpi != item["id"]:
                raise ValueError(f"{item['id']}: falta ligação explícita no panorama")
            generated.dimensions[item["id"]] = {
                "classification": detail.cid,
                "partition": detail.partition,
                "label": detail.name,
            }
            generated.portal.append(
                (
                    theme,
                    subtheme,
                    PanoramaKpi(
                        id=item["id"],
                        label=item["label"],
                        tabela=table,
                        pesquisa=parent.pesquisa,
                    ),
                )
            )
    return generated


def write_agro(root: Path) -> Generated:
    """Grava os fragmentos agropecuários sem modificar os demais catálogos."""
    generated = generate_agro(root)
    outputs = {
        root / "sources/ibge-medidas-agro.toml": render_sources(generated),
        root / "indicators/demografia/medidas_agro.toml": render_indicators(
            generated, "demografia"
        ),
        root / "portal/demografia/medidas_agro.toml": render_portal(generated, "demografia"),
    }
    for path, contents in outputs.items():
        path.write_text(HEADER + "\n" + contents[contents.index("config_version =") :])
    return generated
