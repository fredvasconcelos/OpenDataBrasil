"""Geração das configurações dos KPIs de Total do panorama (ADR-0010, onda de Totais).

A partir do panorama (``configs/catalog/panorama.toml``), da verificação na
fonte (``panorama_verificacao.json``) e do snapshot do acervo, gera três
fragmentos, sem tocar nos arquivos curados à mão:

* fontes: um dataset SIDRA por tabela (``configs/sources/<arquivo>``);
* catálogo semântico: um fato e um indicador por KPI
  (``configs/indicators/<escopo>/<arquivo>``);
* portal: um KPI por item, com o ``id`` do item (``configs/portal/<escopo>/<arquivo>``).

Só entram KPIs cujo valor publicado é o próprio Total da tabela: período
anual, toda classificação numa categoria única com nome (o Total ou a
categoria-padrão da tabela), nível Brasil, Região, UF ou Município, e uma
variável com unidade única. As classificações viram ``fixed_categories``: a
Gold confere a categoria e retira a dimensão. Nenhum código é inventado: tudo
vem da verificação na fonte.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from odb_semantics import Panorama, PanoramaKpi, PanoramaSubtheme, PanoramaTheme

GENERATED_HEADER = (
    "# Gerado por `odb panorama gerar` a partir de configs/catalog/panorama.toml e\n"
    "# configs/catalog/panorama_verificacao.json (ADR-0010). Não editar à mão:\n"
    "# ajuste o panorama e gere de novo.\n"
)
SUPPORTED_LEVELS = ("n1", "n2", "n3", "n6")
LEVEL_LABELS = {"n1": "Brasil", "n2": "Grande Região", "n3": "UF", "n6": "Município"}
# Linhas por nível numa requisição (a API devolve a lista de territórios do nível).
MAX_ROWS_PER_LEVEL = {"n1": 1, "n2": 5, "n3": 27, "n6": 5600}
# Variáveis que não são o KPI: precisão da estimativa e distribuições (100% no Total).
NOT_KPI = re.compile(
    r"^Coeficiente de variação|intervalo de confiança|percentual do total geral|"
    r"^Distribuição percentual|^Distribuição d",
    re.IGNORECASE,
)
OLD_SERIES_YEAR = 2015
# Notas oficiais copiadas para o indicador; o restante fica na tabela oficial.
MAX_NOTES = 8
_TAG = re.compile(r"<[^>]+>")
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
SOURCE_ID = "ibge-sidra"
LICENSE_ID = "ibge-reuso-com-citacao"


@dataclass
class Generated:
    """Fragmentos gerados e os KPIs deixados de fora, com o motivo."""

    datasets: list[dict[str, Any]] = field(default_factory=list)
    facts: list[dict[str, Any]] = field(default_factory=list)
    indicators: list[dict[str, Any]] = field(default_factory=list)
    portal: list[tuple[PanoramaTheme, PanoramaSubtheme, PanoramaKpi]] = field(default_factory=list)
    skipped: list[tuple[str, str, str]] = field(default_factory=list)  # (kpi, tabela, motivo)


def pick_variable(kpi: PanoramaKpi, info: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Variável do KPI: a fixada em ``variavel`` ou a primeira que é o próprio KPI."""
    variables: list[dict[str, Any]] = info.get("variables") or []
    if kpi.variavel is not None:
        chosen = next((v for v in variables if v["id"] == kpi.variavel), None)
        if chosen is None:
            return None, f"variável {kpi.variavel} não existe na tabela verificada"
    else:
        chosen = next((v for v in variables if not NOT_KPI.search(v["name"])), None)
        if chosen is None:
            return None, "nenhuma variável além de coeficientes e distribuições"
    units = chosen.get("units") or []
    if len(units) != 1:
        found = ", ".join(units) or "sem unidade no Total"
        return None, f"variável {chosen['id']}: unidade não é única ({found})"
    return chosen, ""


def _reason(kpi: PanoramaKpi, info: Mapping[str, Any] | None) -> str:
    """Motivo para deixar o KPI de fora desta onda ('' se entra)."""
    if kpi.requer_categoria:
        return "o Total é só o universo da tabela: entra com as categorias (onda Total + %)"
    if info is None or info.get("status") != "ok":
        return f"tabela não verificada na fonte ({(info or {}).get('error', 'sem verificação')})"
    if info.get("period_label") != "Ano":
        return f"períodos por {info.get('period_label')}: a Gold só aceita anos nesta versão"
    no_total = [
        c["label"]
        for c in info.get("classifications") or []
        if len(c.get("categories") or []) != 1 or not c["categories"][0].get("name")
    ]
    if no_total:
        return f"sem categoria Total em: {', '.join(no_total)}"
    if info.get("base_level") not in SUPPORTED_LEVELS:
        return f"dados no nível {info.get('base_level')}: a Gold ainda não tem esse nível"
    return ""


def _levels(info: Mapping[str, Any]) -> list[str]:
    levels = info.get("levels") or {}
    return [lv for lv in SUPPORTED_LEVELS if levels.get(lv)]


def _periodicity(periods: list[str]) -> str:
    years = [int(p) for p in periods if p.isdigit()]
    if len(years) > 1 and all(b - a == 1 for a, b in pairwise(years)):
        return "anual"
    return "anos de referência da pesquisa" if len(years) > 1 else "período único"


def official_notes(descriptor: Mapping[str, Any] | None) -> list[str]:
    """Notas do descritor (HTML) em linhas de texto."""
    raw = (descriptor or {}).get("Nota") or ""
    lines = [html.unescape(_TAG.sub("", part)).replace("\xa0", " ") for part in _BREAK.split(raw)]
    return [" ".join(line.split()) for line in lines if line.strip()]


def _caveats(
    kpi: PanoramaKpi,
    info: Mapping[str, Any],
    levels: list[str],
    descriptor: Mapping[str, Any] | None,
) -> list[str]:
    out = []
    if "n1" not in levels:
        shown = ", ".join(LEVEL_LABELS[lv] for lv in levels)
        out.append(
            f"A fonte não publica esta tabela para o Brasil: os dados vêm por {shown}, "
            "como publicados (tabela SIDRA "
            f"{kpi.tabela})."
        )
    last = (info.get("periods") or [""])[-1][:4]
    if last.isdigit() and int(last) < OLD_SERIES_YEAR:
        out.append(f"Série encerrada na fonte em {last}: é a série publicada, sem atualização.")
    if kpi.nota:
        out.append(kpi.nota)
    notes = official_notes(descriptor)
    out += [f"Nota da tabela {kpi.tabela}: {n}" for n in notes[:MAX_NOTES]]
    if len(notes) > MAX_NOTES:
        out.append(f"Mais {len(notes) - MAX_NOTES} notas na tabela oficial (SIDRA {kpi.tabela}).")
    return out


def _additivity(descriptor: Mapping[str, Any] | None, variable: str) -> str:
    """Aditiva só quando o descritor oficial permite somar entre territórios."""
    for var in (descriptor or {}).get("Variaveis") or []:
        if str(var.get("Id")) == variable:
            return "additive" if var.get("PermiteSomaUnidadesTerritoriais") else "non_additive"
    return "non_additive"


def generate(
    panorama: Panorama,
    verification: Mapping[str, Any],
    titles: Mapping[str, str],
    *,
    configured_tables: Mapping[str, str],
    existing_indicators: Iterable[str],
    existing_portal_kpis: Iterable[str],
    descriptors: Mapping[str, Mapping[str, Any]] | None = None,
) -> Generated:
    """Configurações dos KPIs de Total elegíveis.

    ``configured_tables`` (tabela → dataset) são as tabelas já configuradas em
    arquivos curados: os KPIs delas ficam de fora (a ligação é manual).
    ``descriptors`` (tabela → ``/DescritoresTabela``) dão a aditividade, a fonte
    e as notas oficiais; sem descritor, o indicador fica não aditivo.
    """
    descriptors = descriptors or {}
    tables = {t["table"]: t for t in verification.get("tables", [])}
    taken = set(existing_indicators) | set(existing_portal_kpis)
    out = Generated()
    seen_tables: set[str] = set()
    for theme, sub, kpi in panorama.items():
        if kpi.kpi is not None:
            continue  # publicado por configuração curada
        if kpi.tabela in configured_tables:
            out.skipped.append(
                (kpi.id, kpi.tabela, f"tabela já configurada ({configured_tables[kpi.tabela]})")
            )
            continue
        info = tables.get(kpi.tabela)
        reason = _reason(kpi, info)
        variable: dict[str, Any] | None = None
        if not reason and info is not None:
            variable, reason = pick_variable(kpi, info)
        if reason or info is None or variable is None:
            out.skipped.append((kpi.id, kpi.tabela, reason))
            continue
        if kpi.id in taken:
            msg = f"{kpi.id}: identificador já usado por um indicador ou KPI curado"
            raise ValueError(msg)
        if kpi.tabela in seen_tables:
            msg = f"tabela {kpi.tabela} em mais de um KPI de Total: separe por variável à mão"
            raise ValueError(msg)
        seen_tables.add(kpi.tabela)
        levels = _levels(info)
        dataset_id = f"ibge-sidra-{kpi.tabela}"
        fact_id = f"fact_sidra_{kpi.tabela}"
        fixed = {c["label"]: c["categories"][0]["id"] for c in info.get("classifications") or []}
        rows = sum(MAX_ROWS_PER_LEVEL[lv] for lv in levels)
        title = titles[kpi.tabela]
        descriptor = descriptors.get(kpi.tabela)
        fonte = (descriptor or {}).get("Fonte")
        at = "; ".join(
            f"{c['label']}: {c['categories'][0]['name']}" for c in info.get("classifications") or []
        )
        out.datasets.append(
            {
                "id": dataset_id,
                "source": SOURCE_ID,
                "official_id": kpi.tabela,
                "title": title,
                "description": (
                    f"Tabela SIDRA {kpi.tabela}, variável {variable['id']} "
                    f"({variable['name']}), no Total das classificações"
                    + (f" ({at})" if at else "")
                    + f". KPI de panorama '{kpi.label}' (ADR-0010)."
                ),
                "license": LICENSE_ID,
                "access_classification": "public_conditional",
                "periodicity": _periodicity(info.get("periods") or []),
                "reference_url": f"https://sidra.ibge.gov.br/tabela/{kpi.tabela}",
                "params": {
                    "table": kpi.tabela,
                    "variables": [variable["id"]],
                    "territorial_levels": levels,
                    "period_discovery_level": levels[0],
                    "estimated_values_per_period": rows,
                    "min_rows": 1,
                    "max_rows": rows,
                    "refresh_recent_periods": 1,
                },
                "silver": {"transformer": "sidra_observation", "territorial_reference": "ibge-dtb"},
            }
        )
        grain = " x ".join([f"território ({', '.join(LEVEL_LABELS[lv] for lv in levels)})", "ano"])
        if kpi.pausado:
            # Em espera: o dataset fica nas fontes (para repescar), fora do catálogo e do portal.
            out.skipped.append((kpi.id, kpi.tabela, f"em espera: {kpi.pausado}"))
            continue
        out.facts.append(
            {
                "id": fact_id,
                "dataset": dataset_id,
                "grain": grain,
                "description": f"{kpi.label}: Total da tabela SIDRA {kpi.tabela} ({title}).",
                "fixed_categories": fixed,
            }
        )
        out.indicators.append(
            {
                "id": kpi.id,
                "name": variable["name"],
                "description": (
                    f"{variable['name']} ({kpi.pesquisa}, tabela SIDRA {kpi.tabela}). "
                    + (f"Valores no Total: {at}." if at else "Tabela sem classificações.")
                    + (f" Fonte: {fonte}." if fonte else "")
                ),
                "dataset": dataset_id,
                "variable": variable["id"],
                "fact": fact_id,
                "column": "valor",
                "unit": variable["units"][0],
                "additivity": _additivity(descriptor, variable["id"]),
                "concept": kpi.id,
                "path": [theme.label, sub.label],
                "caveats": _caveats(kpi, info, levels, descriptor),
            }
        )
        out.portal.append((theme, sub, kpi))
    return out


# ------------------------------------------------------------------ TOML


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_value(v) for v in value) + "]"
    if isinstance(value, dict):
        items = ", ".join(
            f"{json.dumps(k, ensure_ascii=False)} = {_value(v)}" for k, v in value.items()
        )
        return "{ " + items + " }" if items else "{}"
    msg = f"valor sem representação TOML: {value!r}"
    raise TypeError(msg)


def _table(header: str, data: Mapping[str, Any], nested: Iterable[str] = ()) -> list[str]:
    lines = [f"[[{header}]]"]
    lines += [f"{k} = {_value(v)}" for k, v in data.items() if k not in nested]
    for key in nested:
        lines += ["", f"[{header}.{key}]"]
        lines += [f"{k} = {_value(v)}" for k, v in data[key].items()]
    return [*lines, ""]


def render_sources(gen: Generated) -> str:
    """Fragmento de fontes (só datasets; fonte e licença vêm de ``ibge.toml``)."""
    lines = [GENERATED_HEADER, 'config_version = "1.0.0"', ""]
    for ds in gen.datasets:
        lines += _table("datasets", ds, nested=("params", "silver"))
    return "\n".join(lines).rstrip() + "\n"


def render_indicators(gen: Generated, scope: str) -> str:
    """Fragmento do catálogo semântico (fatos e indicadores)."""
    lines = [GENERATED_HEADER, 'config_version = "1.0.0"', f"scope = {_value(scope)}", ""]
    for fact in gen.facts:
        lines += _table("facts", fact)
    for ind in gen.indicators:
        lines += _table("indicators", ind)
    return "\n".join(lines).rstrip() + "\n"


def render_portal(gen: Generated, scope: str) -> str:
    """Fragmento do portal: temas e subtemas do panorama, KPIs com o id do item."""
    lines = [GENERATED_HEADER, 'config_version = "1.0.0"', f"scope = {_value(scope)}", ""]
    current: tuple[str, str] | None = None
    current_theme: str | None = None
    for theme, sub, kpi in gen.portal:
        if theme.id != current_theme:
            lines += ["[[themes]]", f"id = {_value(theme.id)}"]
            lines += [f"label = {_value(theme.label)}", ""]
            current_theme = theme.id
        if (theme.id, sub.id) != current:
            lines += [
                "[[themes.subthemes]]",
                f"id = {_value(sub.id)}",
                f"label = {_value(sub.label)}",
                "",
            ]
            current = (theme.id, sub.id)
        lines += [
            "[[themes.subthemes.kpis]]",
            f"id = {_value(kpi.id)}",
            f"label = {_value(kpi.label)}",
            f"indicator = {_value(kpi.id)}",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def render_report(gen: Generated) -> str:
    """Resumo em texto: gerados e deixados de fora, com o motivo."""
    lines = [f"{len(gen.indicators)} KPIs de Total gerados ({len(gen.datasets)} tabelas)."]
    if gen.skipped:
        lines.append(f"{len(gen.skipped)} KPIs planejados ficaram de fora:")
        lines += [f"  {kpi} ({table}): {why}" for kpi, table, why in gen.skipped]
    return "\n".join(lines)
