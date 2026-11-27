"""Valida o plano de acumulado entre anos, sem alterar API, Gold ou portal."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from odb_semantics.periods import ancestor, parse_period, parts

# Revisão por conceito e variável: autorização de soma territorial não basta.
# Nestes doze anuais, PermiteSomaPeriodos foi confirmado no descritor oficial.
ANNUAL_SUM = frozenset(
    {
        "casamentos",
        "divorcios",
        "producao_lavouras",
        "valor_producao_lavouras",
        "area_colhida_lavouras",
        "pib_municipios",
        "pib_municipios_v498",
        "pib_municipios_v513",
        "pib_municipios_v525",
        "pib_municipios_v543",
        "pib_municipios_v6575",
        "focos_calor",
    }
)

# Conceitos de fluxo sem regra temporal autorizada neste catálogo. O marcador
# impede que o nome/unidade ou a classificação "additive" liberem a soma sozinhos.
FLOW_REVIEW = frozenset(
    {
        "nascidos_vivos",
        "obitos",
        "mortalidade_materna_v9435",
        "mortalidade_materna_v9436",
        "mortalidade_doencas_cronicas_v12948",
        "sim_obitos_residencia",
        "homicidios_v13533",
        "producao_origem_animal",
        "valor_producao_animal",
        "producao_ovos",
        "producao_mel_la_casulos",
        "aquicultura_valor",
        "aquicultura_peixes",
        "aquicultura_camarao",
        "aquicultura_moluscos",
        "agrotoxicos",
        "fertilizantes",
        "empresas_comerciais",
        "exportacoes_importacoes",
        "exportacoes_importacoes_v2152",
        "exportacoes_importacoes_v2154",
        "servicos_nao_financeiros",
        "viagens",
        "empresas_emprego_formal_v662",
        "microempreendedores_v8890",
        "microempreendedores_v8892",
        "microempreendedores_v8894",
        "nascimentos_empresas",
        "pib_per_capita",
        "desflorestamento_amazonia",
    }
)


def capability(kpi: dict[str, Any], source_rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Avalia o conceito e registra a prova por tabela/variável, sem habilitar nada."""
    identifier = kpi["kpi_id"]
    grain = kpi["time_grains"][0]["grain"]
    rule = kpi.get("time_aggregation")
    if identifier in ANNUAL_SUM:
        if (
            grain != "ano"
            or not source_rules
            or any(r.get("sum_periods") is not True for r in source_rules)
        ):
            raise ValueError(f"{identifier}: perfil anual não corresponde ao descritor oficial")
        verdict = "sum_method_supported"
        reason = "Soma de anos autorizada na variável oficial; universo/unidade devem coincidir."
    elif rule == "sum":
        verdict = "sum_method_supported"
        reason = "Fluxo com soma temporal já declarada; falta o operador entre anos por parte."
    elif rule == "compound":
        verdict = "contiguous_compound_only"
        reason = (
            "Composição vigente de intervalo contíguo completo. Partes sazonais de anos "
            "distintos têm lacunas; não equivalem à inflação acumulada do intervalo."
        )
    elif rule == "last":
        verdict = "comparison_only"
        reason = "Estimativas sucessivas revisam a mesma safra; a soma duplicaria o objeto."
    elif rule == "mean":
        verdict = "comparison_only"
        reason = "Média temporal não autoriza soma entre anos; preservar o método já declarado."
    elif identifier in FLOW_REVIEW:
        verdict = "flow_method_review_required"
        reason = (
            "Conceito candidato a fluxo, mas sem regra de soma temporal neste catálogo; "
            "descritor/nota/universo exigem decisão metodológica antes de liberar."
        )
    else:
        verdict = "comparison_only"
        reason = (
            "Estoque, razão, taxa, média, distribuição ou pesquisa de referência; "
            "comparar valores publicados, sem somar anos nem supor granularidade menor."
        )
    return {
        "kpi_id": identifier,
        "label": kpi["label"],
        "native_grain": grain,
        "current_grains": [g["grain"] for g in kpi["time_grains"]],
        "current_rule": rule,
        "verdict": verdict,
        "reason": reason,
        "comparison": "parts_by_year" if grain != "ano" else "published_years",
        "dimensions": [d["classification_id"] for d in kpi["dimensions"]],
        "levels": kpi["levels"],
        "crossed_levels": kpi["crossed_levels"],
        "crossed": kpi["crossed"],
        "source_rules": source_rules,
        "scope": "method_review; each_cell_requires_joint_data_and_comparability",
    }


def expected_periods(year: int, grain: str) -> list[str]:
    """Gera posições esperadas do calendário; não fabrica observações publicadas."""
    if grain == "ano":
        return [str(year)]
    count, marker = {"mes": (12, "M"), "trimestre": (4, "T"), "semestre": (2, "S")}[grain]
    return [
        f"{year}{marker}{n:02d}" if grain == "mes" else f"{year}{marker}{n}"
        for n in range(1, count + 1)
    ]


def sum_by_part(
    points: list[dict[str, Any]],
    *,
    native_grain: str,
    target_grain: str,
    start_year: int,
    end_year: int,
) -> list[dict[str, Any]]:
    """Protótipo de soma por parte do ano, usando as menores parcelas disponíveis.

    Só executar após confirmar a capacidade de soma e a comparabilidade. O retorno
    serve à auditoria: não é o contrato nem o status de um endpoint publicado.
    """
    if start_year > end_year:
        raise ValueError("Ano inicial maior que o final")
    parts(native_grain, target_grain)  # Impede fabricar meses a partir de trimestres.
    indexed: dict[str, dict[str, Any]] = {}
    for point in points:
        code = point["period"]
        if parse_period(code).grain != native_grain:
            raise ValueError("Mistura de grãos ou subtotal com parcelas na mesma série")
        if code in indexed:
            raise ValueError(f"Período {code} duplicado: separar séries e detalhes antes de somar")
        indexed[code] = point
    groups: dict[str, list[str]] = {}
    for year in range(start_year, end_year + 1):
        for code in expected_periods(year, native_grain):
            target = ancestor(code, target_grain)
            part = target[4:] or "ano"
            groups.setdefault(part, []).append(code)
    return [
        {
            "part": part,
            "start_year": start_year,
            "end_year": end_year,
            **_sum_group(indexed, expected),
        }
        for part, expected in groups.items()
    ]


def _sum_group(indexed: dict[str, dict[str, Any]], expected: list[str]) -> dict[str, Any]:
    """Preserva o subtotal conhecido, sem ignorar sigilo ou incompatibilidade."""
    missing, blocked, numeric, input_warnings = [], [], [], []
    numeric_statuses = {
        "valid",
        "true_zero",
        "rounded_zero",
        "derived_sum",
        "partial_sum",
        "partial_period",
    }
    for code in expected:
        point = indexed.get(code, {"value": None, "status": "absent"})
        status = point["status"]
        if status in {"absent", "not_available"} and point["value"] is None:
            missing.append(code)
        elif status not in numeric_statuses or point["value"] is None:
            blocked.append(code)
        else:
            value = Decimal(str(point["value"]))
            if not value.is_finite():
                raise ValueError(f"Valor não finito em {code}")
            numeric.append((code, value))
            if status in {"partial_sum", "partial_period"}:
                input_warnings.append(code)
    subtotal = sum((v for _, v in numeric), Decimal(0)) if numeric and not blocked else None
    severity = "danger" if subtotal is None else "warning" if missing or input_warnings else None
    return {
        "value": str(subtotal) if subtotal is not None else None,
        "severity": severity,
        "expected": len(expected),
        "with_value": len(numeric),
        "missing": missing,
        "blocked": blocked,
        "input_warnings": input_warnings,
        "contributors": [code for code, _ in numeric],
    }


def source_rules_for(
    indicator: str,
    lineage: list[dict[str, Any]],
    descriptors: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Relaciona a variável real de cada tabela sem herdar a regra de outra medida."""
    rules = []
    for member in lineage:
        if member["indicator_id"] != indicator:
            continue
        descriptor = descriptors.get(member["source_table_id"], {})
        variable: dict[str, Any] = next(
            (
                v
                for v in descriptor.get("Variaveis", [])
                if str(v["Id"]) == member["source_variable_id"]
            ),
            {},
        )
        rules.append(
            {
                "table": member["source_table_id"],
                "variable": member["source_variable_id"],
                "sum_periods": variable.get("PermiteSomaPeriodos"),
                "exception": variable.get("PeriodoDisponibilidadeExcecao", ""),
            }
        )
    return rules


def main() -> None:
    """Confronta todos os KPIs com descritores fixados e séries coletadas em leitura."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source-evidence", type=Path, required=True)
    args = parser.parse_args()
    output, source = args.evidence, args.source_evidence
    navigation = json.loads((output / "portal-navigation.json").read_text())
    gold = json.loads((source / "gold-metadata.json").read_text())
    if navigation["release_id"] != gold["release_id"]:
        raise ValueError("Catálogo e linhagem pertencem a releases diferentes")
    descriptors = {}
    for table, entry in json.loads((source / "indice-descritores.json").read_text()).items():
        body = (source / entry["path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise ValueError(f"Descritor {table} alterado no disco")
        descriptors[table] = json.loads(body)
    catalog = [k for t in navigation["themes"] for s in t["subthemes"] for k in s["kpis"]]
    rows, experiments = [], []
    series_index = json.loads((output / "indice-series.json").read_text())
    for kpi in catalog:
        rules = source_rules_for(kpi["indicator_id"], gold["lineage"], descriptors)
        row = capability(kpi, rules)
        entry = series_index.get(kpi["kpi_id"], {})
        if entry.get("error") or not entry.get("path"):
            raise ValueError(f"Série {kpi['kpi_id']} sem resposta válida: {entry}")
        raw = Path(entry["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Série {kpi['kpi_id']} alterada no disco")
        series = json.loads(raw)
        if series["provenance"]["truncated"] or (
            series["provenance"]["release_id"] != navigation["release_id"]
        ):
            raise ValueError(f"Série {kpi['kpi_id']} truncada ou de outro release")
        row["series_http"] = entry["status"]
        row["sample_geography"] = entry["geography"]
        row["sample_numeric_points"] = sum(
            p["value"] is not None for s in series["series"] for p in s["points"]
        )
        rows.append(row)
        if row["verdict"] == "sum_method_supported":
            targets = [row["native_grain"]]
            if row["native_grain"] == "mes":
                targets.append("trimestre")
            for target in targets:
                for end in (2025, 2026):
                    for observed in series["series"]:
                        experiments.append(
                            {
                                "kpi_id": kpi["kpi_id"],
                                "series": observed["key"],
                                "geography": entry["geography"],
                                "target_grain": target,
                                "end_year": end,
                                "result": sum_by_part(
                                    observed["points"],
                                    native_grain=row["native_grain"],
                                    target_grain=target,
                                    start_year=2023,
                                    end_year=end,
                                ),
                            }
                        )
    (output / "validacao-kpis.json").write_text(
        json.dumps(
            {"release_id": navigation["release_id"], "kpis": rows, "experiments": experiments},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    with (output / "validacao-kpis.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                for k, v in row.items()
            }
            for row in rows
        )
    print(f"KPIs: {len(rows)}; conclusões: {dict(Counter(r['verdict'] for r in rows))}")
    print(f"Experimentos de soma: {len(experiments)}; nenhuma publicação ou escrita na Gold")


if __name__ == "__main__":
    main()
