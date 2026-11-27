"""Revisa o detalhamento oficial e o catálogo publicado, sem publicar dados."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

SIDRA = "https://apisidra.ibge.gov.br"
MIN_INTERVAL = 2.0
HALT_STATUSES = frozenset({403, 405, 429})
Fetch = Callable[[str], tuple[int, bytes]]


def published_kpis(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumera o catálogo realmente publicado, preservando a taxonomia."""
    return [k for t in snapshot["themes"] for s in t["subthemes"] for k in s["kpis"]]


def source_tables(snapshot: dict[str, Any]) -> list[str]:
    """Obtém somente tabelas SIDRA explicitamente ligadas aos KPIs publicados."""
    ids = {
        str(t["table_id"])
        for k in published_kpis(snapshot)
        if k["source"].get("system") == "SIDRA"
        for t in k["source"]["tables"]
    }
    if any(not table.isascii() or not table.isdecimal() for table in ids):
        raise ValueError("Tabela SIDRA sem código numérico oficial no catálogo publicado")
    return sorted(ids, key=int)


def fetch_official(url: str) -> tuple[int, bytes]:
    """GET normal do recurso oficial, sem imitação de navegador ou contorno."""
    try:
        with urllib.request.urlopen(url, timeout=90) as response:  # noqa: S310 - URL oficial fixa
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def collect_descriptors(
    snapshot: dict[str, Any],
    output: Path,
    *,
    fetch: Fetch = fetch_official,
    interval: float = MIN_INTERVAL,
) -> dict[str, Any]:
    """Revalida cada descritor uma vez, com retomada por hash e parada em bloqueio."""
    if interval < MIN_INTERVAL:
        raise ValueError("O intervalo do SIDRA deve ser de pelo menos 2 segundos")
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "descritores"
    raw.mkdir(exist_ok=True)
    index_path = output / "indice-descritores.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    if any(e.get("status") in HALT_STATUSES for e in index.values()):
        raise ValueError("Coleta interrompida pela fonte; não retomar automaticamente")
    previous = float("-inf")
    for number, table in enumerate(source_tables(snapshot), 1):
        entry = index.get(table, {})
        if entry.get("status") == HTTPStatus.OK and not entry.get("error"):
            saved = output / entry["path"]
            if hashlib.sha256(saved.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Descritor {table} mudou no disco; preservar e investigar")
            continue
        time.sleep(max(0.0, interval - (time.monotonic() - previous)))
        request_dir = Path(tempfile.mkdtemp(prefix=f"t{table}-", dir=raw))
        url = f"{SIDRA}/DescritoresTabela/t/{table}"
        entry = {"url": url, "retrieved_at": datetime.now(UTC).isoformat()}
        try:
            previous = time.monotonic()
            status, body = fetch(url)
            saved = request_dir / "resposta.json"
            saved.write_bytes(body)
            entry.update(
                status=status,
                bytes=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
                path=str(saved.relative_to(output)),
            )
            if status == HTTPStatus.OK:
                payload = json.loads(body)
                if not isinstance(payload, dict) or str(payload.get("Id")) != table:
                    raise ValueError(f"Descritor {table} respondeu com outra identificação")
        except (OSError, ValueError) as exc:
            entry["error"] = str(exc)
        index[table] = entry
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        print(
            f"[{number}/{len(source_tables(snapshot))}] tabela {table}: "
            f"{entry.get('status', 'erro')} {entry.get('error', '')}",
            flush=True,
        )
        if entry.get("status") in HALT_STATUSES:
            print(
                "Fonte interrompida: bloqueio/limite respeitado, sem caminho alternativo.",
                flush=True,
            )
            break
    return index


def native_classification(cid: str, table: str) -> str | None:
    """Reconhece apenas ids nativos e aliases por tabela explicitamente usados no catálogo.

    Sufixos de harmonização/agrupamento não comprovam equivalência com a categoria
    nativa. Ficam como derivados para revisão, em vez de casar por nomes semelhantes.
    """
    match = re.fullmatch(r"c(\d+)(?:t(\d+))?", cid)
    if not match or (match[2] and match[2] != table):
        return None
    return match[1]


def sidra_period(period: str) -> str:
    """Converte somente os calendários mensais e trimestrais já usados pelo projeto."""
    match = re.fullmatch(r"(\d{4})[MT](\d{1,2})", period)
    return f"{match[1]}{int(match[2]):02}" if match else period


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    """Grava listas como JSON explícito nas células, sem perder ids ou exceções."""
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False, sort_keys=True)
                    if isinstance(v, (dict, list, tuple))
                    else v
                    for k, v in row.items()
                }
            )


def _native_categories(
    categories: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Preserva a hierarquia da fonte sem tratar pai e filhos como partes disjuntas."""
    stack: list[tuple[int, str]] = []
    result: dict[str, dict[str, Any]] = {}
    for category in categories:
        depth = int(category["NivelIdentacao"])
        while stack and stack[-1][0] >= depth:
            stack.pop()
        identifier = str(category["Id"])
        result[identifier] = {**category, "parent_id": stack[-1][1] if stack else None}
        stack.append((depth, identifier))
    return result


def _load_descriptors(output: Path) -> dict[str, dict[str, Any]]:
    index = json.loads((output / "indice-descritores.json").read_text())
    descriptors = {}
    for table, entry in index.items():
        if entry.get("status") != HTTPStatus.OK or entry.get("error"):
            continue
        body = (output / entry["path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise ValueError(f"Metadado {table} alterado depois da coleta")
        descriptors[table] = json.loads(body)
    return descriptors


def probe_plan(output: Path) -> list[dict[str, Any]]:
    """Planeja amostras pequenas de todos os eixos e variáveis realmente usados.

    Uma amostra testa o pedido conjunto no recorte explícito. Não comprova a
    disponibilidade de todas as categorias, territórios e datas do descritor.
    """
    gold = json.loads((output / "gold-metadata.json").read_text())
    result = []
    for table, descriptor in sorted(_load_descriptors(output).items(), key=lambda x: int(x[0])):
        variables = sorted(
            {m["source_variable_id"] for m in gold["lineage"] if m["source_table_id"] == table},
            key=int,
        )
        declared = {str(v["Id"]) for v in descriptor["Variaveis"]}
        if not variables or not set(variables) <= declared:
            raise ValueError(f"Tabela {table}: variáveis da linhagem sem confirmação oficial")
        levels = descriptor["NiveisTerritoriais"]
        level = next((n for n in levels if str(n["Id"]) == "1"), None)
        if level is None:
            level = min(levels, key=lambda n: n["QuantidadeUnidadesAtivas"])
        period = max(str(p["Codigo"]) for p in descriptor["Periodos"])
        selections = {
            str(c["Id"]): [str(x["Id"]) for x in c["Categorias"][:2]]
            for c in descriptor.get("Classificacoes") or []
        }
        estimated = len(variables) * int(level["QuantidadeUnidadesAtivas"])
        for ids in selections.values():
            estimated *= len(ids)
        if estimated > 1000:  # noqa: PLR2004 - teto conservador da auditoria, não do SIDRA
            raise ValueError(
                f"Tabela {table}: amostra excede 1000 células; fatiar antes de consultar"
            )
        suffix = "".join(f"/c{cid}/{','.join(ids)}" for cid, ids in selections.items())
        url = (
            f"{SIDRA}/values/t/{table}/n{level['Id']}/all"
            f"/v/{','.join(variables)}/p/{period}{suffix}"
        )
        result.append(
            {
                "table": table,
                "variables": variables,
                "period": period,
                "level": str(level["Id"]),
                "categories": selections,
                "estimated_cells": estimated,
                "url": url,
            }
        )
    return result


def collect_probes(output: Path, *, fetch: Fetch = fetch_official) -> dict[str, Any]:
    """Consulta amostras conjuntas em série, preservando erros e valores especiais."""
    plan = probe_plan(output)
    (output / "plano-amostras.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    index_path = output / "indice-amostras.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    if any(e.get("status") in HALT_STATUSES for e in index.values()):
        raise ValueError("Amostragem interrompida pela fonte; não retomar automaticamente")
    previous = float("-inf")
    raw = output / "amostras"
    raw.mkdir(exist_ok=True)
    for number, sample in enumerate(plan, 1):
        table = sample["table"]
        if table in index:
            entry = index[table]
            if entry["url"] != sample["url"]:
                raise ValueError(f"Tabela {table}: plano mudou; usar novo diretório de evidências")
            if hashlib.sha256((output / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Tabela {table}: resposta alterada no disco")
            continue
        time.sleep(max(0.0, MIN_INTERVAL - (time.monotonic() - previous)))
        request_dir = Path(tempfile.mkdtemp(prefix=f"t{table}-", dir=raw))
        previous = time.monotonic()
        status, body = fetch(sample["url"])
        saved = request_dir / "resposta.json"
        saved.write_bytes(body)
        entry = {
            **sample,
            "status": status,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "sha256": hashlib.sha256(body).hexdigest(),
            "path": str(saved.relative_to(output)),
        }
        try:
            payload = json.loads(body)
            if status == HTTPStatus.OK and isinstance(payload, list) and len(payload) > 1:
                entry["rows"] = len(payload) - 1
                entry["numeric_rows"] = sum(
                    bool(re.fullmatch(r"-?\d+(?:\.\d+)?", str(r.get("V", "")))) for r in payload[1:]
                )
                entry["special_values"] = sorted(
                    {
                        str(r.get("V", ""))
                        for r in payload[1:]
                        if not re.fullmatch(r"-?\d+(?:\.\d+)?", str(r.get("V", "")))
                    }
                )
                entry["header"] = payload[0]
            else:
                entry["error"] = body.decode("utf-8", errors="replace")[:1000]
        except ValueError:
            entry["error"] = body.decode("utf-8", errors="replace")[:1000]
        index[table] = entry
        index_path.write_text(json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2))
        print(
            f"[{number}/{len(plan)}] amostra {table}: {status}, "
            f"{entry.get('rows', 0)} células, {entry.get('error', '')[:160]}",
            flush=True,
        )
        if status in HALT_STATUSES:
            break
    return index


def validate_probe(entry: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Confere que a amostra devolvida usa os códigos realmente solicitados."""
    if not rows or {r["D2C"] for r in rows} != set(entry["variables"]):
        raise ValueError(f"Tabela {entry['table']}: variáveis da amostra divergem do pedido")
    if {r["NC"] for r in rows} != {entry["level"]} or {r["D3C"] for r in rows} != {entry["period"]}:
        raise ValueError(f"Tabela {entry['table']}: nível/período da amostra diverge do pedido")
    # A ordem vem da URL preservada, pois o índice JSON ordena as chaves dos objetos.
    axes = re.findall(r"/c(\d+)/([^/]+)", entry["url"])
    for position, (cid, codes) in enumerate(axes, 4):
        if {r[f"D{position}C"] for r in rows} != set(codes.split(",")):
            raise ValueError(f"Tabela {entry['table']}: categorias c{cid} divergem do pedido")
    return {
        key: entry[key]
        for key in (
            "table",
            "variables",
            "period",
            "level",
            "categories",
            "estimated_cells",
            "url",
            "status",
            "sha256",
            "rows",
            "numeric_rows",
            "special_values",
        )
    } | {
        "coordinates_verified": True,
        "returned_expected_row_count": len(rows) == entry["estimated_cells"],
        "scope": "only_requested_coordinates; no_exhaustive_availability_claim",
    }


def _load_probes(output: Path) -> list[dict[str, Any]]:
    index_path = output / "indice-amostras.json"
    if not index_path.exists():
        return []
    result = []
    for entry in json.loads(index_path.read_text()).values():
        if entry.get("status") != HTTPStatus.OK or entry.get("error"):
            continue
        body = (output / entry["path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise ValueError(f"Tabela {entry['table']}: amostra alterada no disco")
        result.append(validate_probe(entry, json.loads(body)[1:]))
    return result


def _class_rows(
    kpi: dict[str, Any],
    table: str,
    descriptor: dict[str, Any],
    observed: dict[tuple[str, str, str], set[str]],
) -> list[dict[str, Any]]:
    """Confronta cada eixo nativo com observações persistidas e opções da API."""
    result = []
    for classification in descriptor.get("Classificacoes") or []:
        cid = str(classification["Id"])
        categories = _native_categories(classification["Categorias"])
        dims = [
            d
            for d in kpi["dimensions"]
            if native_classification(d["classification_id"], table) == cid
        ]
        total_ids = {str(d["total_category_key"]).split(":", 1)[1] for d in dims}
        visible = {c["category_id"] for d in dims for c in d["categories"]} | total_ids
        stored = observed.get((kpi["indicator_id"], table, cid), set()) | (
            total_ids & set(categories)
        )
        result.append(
            {
                "kpi_id": kpi["kpi_id"],
                "table": table,
                "classification_id": cid,
                "classification": classification["Nome"],
                "source_categories": list(categories),
                "source_category_metadata": list(categories.values()),
                "source_category_count": len(categories),
                "gold_categories": sorted(stored & set(categories)),
                "gold_category_scope": "any_period_level_variable; totals_from_configuration",
                "api_categories": sorted(visible & set(categories)),
                "not_in_gold": sorted(set(categories) - stored),
                "not_in_api": sorted(set(categories) - visible),
                "loaded_not_exposed": sorted((set(categories) & stored) - visible),
                "api_dimensions": [d["classification_id"] for d in dims],
                "can_sum": classification.get("CategoriasPodemSerSomadas"),
                "exceptions": {
                    key: c.get("PeriodoDisponibilidadeExcecao", "")
                    for key, c in categories.items()
                    if c.get("PeriodoDisponibilidadeExcecao")
                },
                "hierarchy": {key: c["parent_id"] for key, c in categories.items()},
            }
        )
    return result


def _cross_rows(
    kpi: dict[str, Any],
    member: dict[str, Any],
    descriptor: dict[str, Any],
    classes: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
    *,
    level_ids: dict[str, str],
) -> list[dict[str, Any]]:
    """Enumera todos os conjuntos de eixos sem misturar tabelas ou variáveis."""
    result = []
    cids = [c["classification_id"] for c in classes]
    aliases = {c["classification_id"]: c["api_dimensions"] for c in classes}
    for size in range(2, len(cids) + 1):
        for group in itertools.combinations(cids, size):
            requested = [aliases[c][0] for c in group if aliases[c]]
            for level in descriptor.get("NiveisTerritoriais") or []:
                sidra_level = str(level["Id"])
                internal = level_ids.get(sidra_level)
                configured = (
                    len(requested) == size
                    and internal in kpi["levels"]
                    and (
                        not kpi["exclusive_dimensions"]
                        or (
                            internal in kpi["crossed_levels"]
                            and any(set(requested) <= set(g) for g in kpi["crossed"])
                        )
                    )
                )
                periods = [
                    p["period"]
                    for p in patterns
                    if p["level_id"] == internal
                    and {
                        native_classification(d, str(member["source_table_id"]))
                        for d in p["dimensions"]
                    }
                    == set(group)
                ]
                result.append(
                    {
                        "kpi_id": kpi["kpi_id"],
                        "table": member["source_table_id"],
                        "variable": member["source_variable_id"],
                        "classifications": list(group),
                        "sidra_level": sidra_level,
                        "level_name": level["Nome"],
                        "portal_level": internal or "not_mapped_in_model",
                        "api_config_allows": configured,
                        "gold_has_joint_observations": bool(periods),
                        "gold_periods_with_joint_observations": sorted(set(periods)),
                        "source_proof": "descriptor_axes_only_requires_values_and_notes",
                        "level_exception": level.get("PeriodoDisponibilidadeExcecao", ""),
                    }
                )
    return result


def compare_catalog(snapshot: dict[str, Any], output: Path, coverage: Path) -> None:
    """Produz a matriz integral fonte/Gold/API a partir de evidências fixadas."""
    import polars as pl  # noqa: PLC0415 - a coleta de metadados usa somente a biblioteca padrão

    from odb_modeling.model import SIDRA_LEVELS  # noqa: PLC0415 - reutiliza o mapeamento executável

    descriptors = _load_descriptors(output)
    gold = json.loads((output / "gold-metadata.json").read_text())
    pattern_data = json.loads((output / "gold-cruzamentos.json").read_text())
    prior = json.loads((coverage / "catalogo-api.json").read_text())
    if (
        snapshot["release_id"] != gold["release_id"]
        or gold["release_id"] != pattern_data["release_id"]
        or gold["release_id"] != prior["release_id"]
        or gold["tables"] != prior["tables"]
    ):
        raise ValueError("Snapshots de releases diferentes; não produzir comparação misturada")
    details = pl.read_parquet(coverage / "detalhes.parquet").to_dicts()
    observed: dict[tuple[str, str, str], set[str]] = {}
    for row in details:
        table = str(row["source_table_id"])
        native = native_classification(row["classification_id"], table)
        if native:
            target = observed.setdefault((row["indicator_id"], table, native), set())
            target.update(c["category_key"].split(":", 1)[1] for c in row["category_territories"])
    axes: list[dict[str, Any]] = []
    crosses: list[dict[str, Any]] = []
    levels: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    calendars: list[dict[str, Any]] = []
    variables: list[dict[str, Any]] = []
    for table, descriptor in descriptors.items():
        members = [m for m in gold["lineage"] if m["source_table_id"] == table]
        for variable in descriptor["Variaveis"]:
            variables.append(
                {
                    "table": table,
                    "variable": str(variable["Id"]),
                    "name": variable["Nome"],
                    "unit": variable["UnidadeMedida"],
                    "type": variable["Tipo"],
                    "linked_indicators": sorted(
                        {
                            m["indicator_id"]
                            for m in members
                            if m["source_variable_id"] == str(variable["Id"])
                        }
                    ),
                    "can_sum_periods": variable.get("PermiteSomaPeriodos"),
                    "can_sum_territories": variable.get("PermiteSomaUnidadesTerritoriais"),
                    "storage_decimals": variable.get("CasasDecimaisArmazenamento"),
                    "display_decimals": variable.get("CasasDecimaisApresentacao"),
                    "exception": variable.get("PeriodoDisponibilidadeExcecao", ""),
                }
            )
    for kpi in published_kpis(snapshot):
        members = [m for m in gold["lineage"] if m["indicator_id"] == kpi["indicator_id"]]
        own_axes, own_crosses = [], []
        for member in members if kpi["source"].get("system") == "SIDRA" else []:
            table = str(member["source_table_id"])
            if table not in descriptors:
                continue
            descriptor = descriptors[table]
            member_axes = _class_rows(kpi, table, descriptor, observed)
            for axis in member_axes:
                axis["variable"] = member["source_variable_id"]
            own_axes.extend(member_axes)
            source_periods = {str(p["Codigo"]) for p in descriptor["Periodos"]}
            gold_periods = {sidra_period(p) for p in member["periods"]}
            calendars.append(
                {
                    "kpi_id": kpi["kpi_id"],
                    "table": table,
                    "variable": member["source_variable_id"],
                    "source_period_type": descriptor["TipoPeriodo"],
                    "source_periods": sorted(source_periods),
                    "gold_periods": sorted(gold_periods),
                    "source_periods_not_in_gold": sorted(source_periods - gold_periods),
                    "gold_periods_not_in_source": sorted(gold_periods - source_periods),
                    "requires_calendar_review": bool(gold_periods - source_periods),
                    "scope": "table_calendar; variable_category_level_exceptions_apply",
                }
            )
            patterns = [
                p
                for p in pattern_data["rows"]
                if p["indicator_id"] == kpi["indicator_id"]
                and p["source_table_id"] == table
                and p["source_variable_id"] == member["source_variable_id"]
            ]
            own_crosses.extend(
                _cross_rows(kpi, member, descriptor, member_axes, patterns, level_ids=SIDRA_LEVELS)
            )
            for level in descriptor.get("NiveisTerritoriais") or []:
                identifier = str(level["Id"])
                internal = SIDRA_LEVELS.get(identifier)
                levels.append(
                    {
                        "kpi_id": kpi["kpi_id"],
                        "table": table,
                        "variable": member["source_variable_id"],
                        "sidra_level": identifier,
                        "name": level["Nome"],
                        "portal_level": internal or "not_mapped_in_model",
                        "api_exposes": internal in kpi["levels"],
                        "gold_has_level": internal in member["levels"],
                        "exception": level.get("PeriodoDisponibilidadeExcecao", ""),
                    }
                )
        axes.extend(own_axes)
        crosses.extend(own_crosses)
        summaries.append(
            {
                "kpi_id": kpi["kpi_id"],
                "label": kpi["label"],
                "theme_id": kpi["theme_id"],
                "source": kpi["source"].get("system") or kpi["source"].get("institution"),
                "indicator_id": kpi["indicator_id"],
                "tables": sorted({m["source_table_id"] for m in members}),
                "source_axis_records": len(own_axes),
                "source_categories_not_in_api": sum(len(a["not_in_api"]) for a in own_axes),
                "source_categories_not_in_gold": sum(len(a["not_in_gold"]) for a in own_axes),
                "loaded_categories_not_exposed": sum(
                    len(a["loaded_not_exposed"]) for a in own_axes
                ),
                "crossing_records": len(own_crosses),
                "crossings_blocked_by_config": sum(not c["api_config_allows"] for c in own_crosses),
                "crossings_without_joint_gold": sum(
                    not c["gold_has_joint_observations"] for c in own_crosses
                ),
                "status": "compared_metadata_requires_source_probes"
                if own_axes or kpi["source"].get("system") == "SIDRA"
                else "review_in_original_source_not_sidra",
            }
        )
    result = {
        "release_id": snapshot["release_id"],
        "kpis": summaries,
        "axes": axes,
        "crossings": crosses,
        "levels": levels,
        "calendars": calendars,
        "variables": variables,
        "source_samples": _load_probes(output),
        "source_notes": [
            {
                "table": table,
                "note": d.get("Nota"),
                "source": d.get("Fonte"),
                "updated_at": d.get("DataAtualizacao"),
                "period_type": d.get("TipoPeriodo"),
                "reference_url": f"{SIDRA}/DescritoresTabela/t/{table}",
            }
            for table, d in descriptors.items()
        ],
    }
    (output / "matriz.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    for name, records in [
        ("kpis", summaries),
        ("detalhamentos", axes),
        ("cruzamentos", crosses),
        ("niveis", levels),
        ("periodos", calendars),
        ("variaveis", variables),
        ("notas-fontes", result["source_notes"]),
        ("amostras-fonte", result["source_samples"]),
    ]:
        write_csv(output / f"{name}.csv", records)
    print(
        f"Matriz: {len(summaries)} KPIs, {len(axes)} eixos, "
        f"{len(crosses)} cruzamentos por tabela/variável/nível",
        flush=True,
    )


def main() -> None:
    """Executa a etapa de metadados em diretório de evidências próprio."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--coverage", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    if args.probe:
        probes = collect_probes(args.output)
        tables = source_tables(snapshot)
        if any(
            probes.get(t, {}).get("status") != HTTPStatus.OK or probes[t].get("error")
            for t in tables
        ):
            raise SystemExit(1)
        return
    if args.compare:
        if args.coverage is None:
            parser.error("--compare exige --coverage com as evidências da Gold fixada")
        compare_catalog(snapshot, args.output, args.coverage)
        return
    index = collect_descriptors(snapshot, args.output)
    tables = source_tables(snapshot)
    successful = sum(
        index.get(t, {}).get("status") == HTTPStatus.OK and not index[t].get("error")
        for t in tables
    )
    print(f"Descritores confirmados: {successful}/{len(tables)}", flush=True)
    if successful != len(tables):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
