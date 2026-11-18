"""Gera medidas complementares nativas, sem mudar o contrato ou o código do portal."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from odb_cli.panorama_gen import (
    Detail,
    Generated,
    _detail_of,
    _register,
    _total_of,
    level_limits,
    official_notes,
    pick_variable,
    render_indicators,
    render_portal,
    render_sources,
)
from odb_ingestion.connectors.sidra import SidraParams
from odb_semantics import PanoramaKpi, PanoramaSubtheme, PanoramaTheme, load_panorama

HEADER = "# Gerado por `odb panorama gerar-medidas`. Edite catalog/medidas-adicionais.toml.\n"
MUNICIPAL_LEVEL = 6
CAPITAL_COUNT = 27


def available_periods(descriptor: dict[str, Any], exception: str) -> list[str]:
    """Seleciona apenas códigos do descritor dentro dos intervalos oficiais nomeados."""
    periods = descriptor["Periodos"]
    if not exception:
        return [str(p["Codigo"]) for p in periods]
    names = {p["Nome"]: str(p["Codigo"]) for p in periods}
    selected: set[str] = set()
    for interval in exception.split(", "):
        bounds = interval.split(" a ")
        if len(bounds) not in (1, 2) or any(bound not in names for bound in bounds):
            raise ValueError(
                f"tabela {descriptor['Id']}: disponibilidade não reconhecida: {interval}"
            )
        lower, upper = names[bounds[0]], names[bounds[-1]]
        selected.update(str(p["Codigo"]) for p in periods if lower <= str(p["Codigo"]) <= upper)
    return sorted(selected)


def measure_reference(
    descriptor: dict[str, Any], references: dict[str, str]
) -> tuple[dict[str, str], dict[str, str], list[str], list[str]]:
    """Valida referências declaradas e Totais, incluindo o calendário da categoria."""
    known = {f"c{c['Id']}" for c in descriptor["Classificacoes"]}
    unknown = references.keys() - known
    if unknown:
        raise ValueError(
            f"tabela {descriptor['Id']}: classificações inexistentes: {sorted(unknown)}"
        )
    classes: dict[str, str] = {}
    fixed: dict[str, str] = {}
    periods = available_periods(descriptor, "")
    labels = []
    for classification in descriptor["Classificacoes"]:
        key = f"c{classification['Id']}"
        code = references.get(key, _total_of(classification))
        if code is None:
            raise ValueError(
                f"tabela {descriptor['Id']}: {classification['Nome']} sem Total comprovado; "
                "declare referencia com uma categoria oficial"
            )
        category = next((c for c in classification["Categorias"] if str(c["Id"]) == code), None)
        if category is None:
            raise ValueError(f"tabela {descriptor['Id']}: referência {key}={code} inexistente")
        classes[key] = code
        fixed[classification["Nome"]] = code
        calendar = available_periods(descriptor, category.get("PeriodoDisponibilidadeExcecao", ""))
        periods = [p for p in periods if p in calendar]
        if key in references:
            labels.append(f"{classification['Nome']}: {category['Nome']} ({key}={code})")
    return classes, fixed, periods, labels


def measure_detail(
    generated: Generated,
    descriptor: dict[str, Any],
    cid: str | None,
    *,
    dataset_id: str,
    periods: list[str],
    classes: dict[str, str],
    fixed: dict[str, str],
) -> Detail | None:
    """Mantém uma dimensão nativa com hierarquia, sem somar categorias sobrepostas."""
    if cid is None:
        return None
    classification = next((c for c in descriptor["Classificacoes"] if f"c{c['Id']}" == cid), None)
    if classification is None:
        raise ValueError(f"tabela {descriptor['Id']}: detalhe {cid} inexistente")
    limits = level_limits(descriptor).get(classification["Nome"])
    levels = {f"n{n['Id']}" for n in descriptor["NiveisTerritoriais"] if n["Id"] in (1, 2, 3, 6)}
    if limits and not levels <= set(limits):
        raise ValueError(
            f"tabela {descriptor['Id']}: detalhe {cid} exige contrato de níveis próprio"
        )
    for category in classification["Categorias"]:
        calendar = available_periods(descriptor, category.get("PeriodoDisponibilidadeExcecao", ""))
        if not set(periods) <= set(calendar):
            raise ValueError(
                f"tabela {descriptor['Id']}: {cid}/{category['Id']} exige contrato "
                "de calendário próprio"
            )
    detail, reason = _detail_of(classification, {})
    if detail is None:
        raise ValueError(f"tabela {descriptor['Id']}: {reason}")
    # O catálogo principal também usa a classificação. O espaço das medidas
    # mantém seus datasets isolados, como nas coortes agropecuárias (N2, 2026-11-17).
    detail.cid = f"{cid}ma"
    reason = _register(generated, detail, str(descriptor["Id"]), {})
    if reason:
        raise ValueError(reason)
    entry = generated.classifications[detail.cid]
    entry["datasets"] = [d for d in entry["datasets"] if d != f"ibge-sidra-{descriptor['Id']}"]
    if dataset_id not in entry["datasets"]:
        entry["datasets"].append(dataset_id)
    classes[cid] = ",".join(detail.categories)
    del fixed[detail.name]
    return detail


def _publish_measure(
    generated: Generated,
    item: dict[str, Any],
    parents: dict[str, tuple[PanoramaTheme, PanoramaSubtheme, PanoramaKpi]],
    detail: Detail | None,
) -> None:
    """Liga uma medida pública ao catálogo, preservando o contexto da fonte real."""
    if not item["publish"]:
        return
    public = parents.get(item["id"])
    if public is None or public[2].kpi != item["id"]:
        raise ValueError(f"{item['id']}: falta ligação explícita no panorama")
    theme, subtheme, parent = parents[item["parent"]]
    if detail:
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
                id=item["id"], label=item["label"], tabela=item["table"], pesquisa=parent.pesquisa
            ),
        )
    )


def validate_measure_support(items: list[dict[str, Any]]) -> None:
    """Exige ligação explícita entre IC95 oculto e estimativa do mesmo recorte."""
    measures = {item["id"]: item for item in items}
    for item in items:
        if "support_of" not in item:
            continue
        estimate = measures.get(item["support_of"])
        if estimate is None or item["publish"] or not estimate["publish"]:
            raise ValueError(
                f"{item['id']}: suporte exige estimativa pública e não pode ser publicado"
            )
        for field in ("table", "parent", "referencia", "detail"):
            if item.get(field) != estimate.get(field):
                raise ValueError(f"{item['id']}: suporte e estimativa diferem no recorte {field}")


def validate_primary_support(
    item: dict[str, Any], parent: PanoramaKpi, descriptor: dict[str, Any]
) -> None:
    """Liga suporte à variável principal já publicada, sem duplicar a estimativa."""
    variable = item.get("support_of_primary")
    if variable is None:
        return
    chosen, reason = pick_variable(
        parent,
        {
            "variables": [
                {"id": str(v["Id"]), "name": v["Nome"], "units": [v["UnidadeMedida"]]}
                for v in descriptor["Variaveis"]
            ]
        },
    )
    if (
        item["publish"]
        or item["table"] != parent.tabela
        or item.get("referencia")
        or chosen is None
        or chosen["id"] != variable
    ):
        raise ValueError(f"{item['id']}: suporte da variável principal não comprovado; {reason}")


def generate_measures(root: Path) -> Generated:
    """Compila a seleção revisada contra descritores, unidades e calendários oficiais."""
    spec = tomllib.loads((root / "catalog/medidas-adicionais.toml").read_text())
    validate_measure_support(spec["measures"])
    panorama = load_panorama(root / "catalog/panorama.toml")
    parents = {k.id: (t, s, k) for t, s, k in panorama.items()}
    generated = Generated()
    seen: set[tuple[str, str]] = set()
    for item in spec["measures"]:
        table, variable = item["table"], item["variable"]
        if (table, variable) in seen:
            raise ValueError(f"medida repetida: {table}/{variable}")
        seen.add((table, variable))
        descriptor = json.loads((root / f"catalog/descritores/t{table}.json").read_text())
        measure = next((v for v in descriptor["Variaveis"] if str(v["Id"]) == variable), None)
        if measure is None:
            raise ValueError(f"variável {variable} não existe no descritor da tabela {table}")
        theme, subtheme, parent = parents[item["parent"]]
        validate_primary_support(item, parent, descriptor)
        if table not in (parent.tabela, *parent.complementos):
            raise ValueError(f"{item['id']}: tabela não declarada entre as fontes do KPI de origem")
        periods = available_periods(descriptor, measure.get("PeriodoDisponibilidadeExcecao", ""))
        classes, fixed, category_periods, references = measure_reference(
            descriptor, item.get("referencia", {})
        )
        periods = [p for p in periods if p in category_periods]
        if not periods:
            raise ValueError(f"tabela {table}, variável {variable}: seleção sem períodos comuns")
        dataset_id, fact_id = (
            f"ibge-medida-t{table}-v{variable}",
            f"fact_medida_t{table}_v{variable}",
        )
        if item.get("detail") in item.get("referencia", {}):
            raise ValueError(f"{item['id']}: detalhe também declarado como referência fixa")
        detail = measure_detail(
            generated,
            descriptor,
            item.get("detail"),
            dataset_id=dataset_id,
            periods=periods,
            classes=classes,
            fixed=fixed,
        )
        levels = [
            f"n{n['Id']}" for n in descriptor["NiveisTerritoriais"] if n["Id"] in (1, 2, 3, 6)
        ]
        level_periods = {
            f"n{n['Id']}": [
                p
                for p in available_periods(descriptor, n["PeriodoDisponibilidadeExcecao"])
                if p in periods
            ]
            for n in descriptor["NiveisTerritoriais"]
            if f"n{n['Id']}" in levels and n.get("PeriodoDisponibilidadeExcecao")
        }
        quarterly, monthly = (
            descriptor["TipoPeriodo"] == "Trimestre",
            descriptor["TipoPeriodo"] == "Mês",
        )
        if descriptor["TipoPeriodo"] not in ("Ano", "Trimestre", "Mês"):
            raise ValueError(f"{table}: tipo de período ainda não contemplado nesta seleção")
        count = sum(
            n["QuantidadeUnidadesAtivas"]
            for n in descriptor["NiveisTerritoriais"]
            if f"n{n['Id']}" in levels
        )
        maximum = min(
            50000,
            (count + 40)
            * (12 if monthly else 4 if quarterly else 1)
            * (len(detail.categories) if detail else 1),
        )
        params = {
            "table": table,
            "variables": [variable],
            "territorial_levels": levels,
            "periods": periods,
            "classifications": classes,
            "period_type": "mes" if monthly else "trimestre" if quarterly else "ano",
            "group_periods_by_year": quarterly or monthly,
            "level_periods": level_periods,
            "estimated_values_per_period": maximum,
            "min_rows": 1,
            "max_rows": maximum,
            "refresh_recent_periods": 1,
        }
        if "n1" not in levels:
            # A 5945 só publica GR/UF: a descoberta de períodos também precisa
            # usar um nível nativo, além da consulta de captura (N1, 2026-11-17).
            params["period_discovery_level"] = levels[0]
        SidraParams.model_validate(params)
        notes = [
            f"Medida nativa da tabela SIDRA {table}, variável {variable}, "
            + (
                f"nas categorias nativas de {detail.name}; demais classificações no Total"
                if detail
                else (
                    "na referência " + "; ".join(references)
                    if references
                    else "no Total das classificações"
                )
            )
            + ". Não herda cruzamentos ou detalhamentos de outras tabelas.",
            "Médias, razões, taxas e limites de confiança mantêm os valores oficiais; "
            "não são obtidos pela soma de municípios, UFs ou categorias.",
            *item.get("notes", []),
            *official_notes(descriptor),
        ]
        if level_periods:
            notes.append(
                "Os níveis territoriais respeitam as interrupções de divulgação "
                "do descritor. Períodos sem recorte local não recebem estimativas."
            )
        if measure.get("PeriodoDisponibilidadeExcecao"):
            notes.append(
                "Calendário próprio da variável: " + measure["PeriodoDisponibilidadeExcecao"] + "."
            )
        if any(
            n["Id"] == MUNICIPAL_LEVEL and n["QuantidadeUnidadesAtivas"] == CAPITAL_COUNT
            for n in descriptor["NiveisTerritoriais"]
        ):
            notes.append("A cobertura municipal desta pesquisa se restringe às 27 capitais.")
        generated.datasets.append(
            {
                "id": dataset_id,
                "source": "ibge-sidra",
                "official_id": table,
                "title": measure["Nome"],
                "description": notes[0],
                "license": "ibge-reuso-com-citacao",
                "access_classification": "public_conditional",
                "periodicity": "mensal" if monthly else "trimestral" if quarterly else "anual",
                "reference_url": f"https://sidra.ibge.gov.br/tabela/{table}",
                "params": params,
                "silver": {
                    "transformer": "sidra_observation",
                    "territorial_reference": "ibge-dtb",
                    "panorama_support": True,
                },
            }
        )
        generated.facts.append(
            {
                "id": fact_id,
                "dataset": dataset_id,
                "grain": (
                    "território x mês"
                    if monthly
                    else "território x trimestre"
                    if quarterly
                    else "território x ano"
                )
                + (f" x {detail.name}" if detail else ""),
                "description": measure["Nome"],
                "fixed_categories": fixed,
                **(
                    {"classifications": {detail.cid: f"{detail.cid}_category_key"}}
                    if detail
                    else {}
                ),
            }
        )
        generated.indicators.append(
            {
                "id": item["id"],
                "name": measure["Nome"],
                "description": measure["Nome"],
                "dataset": dataset_id,
                "variable": variable,
                "fact": fact_id,
                "column": "valor",
                "unit": measure["UnidadeMedida"],
                "additivity": "additive"
                if measure.get("PermiteSomaUnidadesTerritoriais")
                else "non_additive",
                "concept": item["id"],
                "path": [theme.label, subtheme.label],
                "caveats": notes,
            }
        )
        _publish_measure(generated, item, parents, detail)
    return generated


def write_measures(root: Path) -> Generated:
    """Grava os três fragmentos reproduzíveis das medidas complementares."""
    generated = generate_measures(root)
    outputs = {
        root / "sources/ibge-medidas-adicionais.toml": render_sources(generated),
        root / "indicators/demografia/medidas_adicionais.toml": render_indicators(
            generated, "demografia"
        ),
        root / "portal/demografia/medidas_adicionais.toml": render_portal(generated, "demografia"),
    }
    for path, contents in outputs.items():
        start = contents.index("config_version =")
        path.write_text(HEADER + "\n" + contents[start:])
    return generated
