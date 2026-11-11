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
# Tipo de período (rótulo da dimensão na API) → tipo do conector e períodos por ano.
PERIOD_TYPES = {"Ano": ("ano", 1), "Mês": ("mes", 12), "Trimestre": ("trimestre", 4)}
# Acima disso, o nível municipal da tabela é o país inteiro (a API devolve todos os
# municípios); abaixo, é um recorte (por exemplo, só as capitais) e vale a contagem.
FULL_MUNICIPAL = 1000
SIDRA_VALUE_LIMIT = 50_000
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
    # Onda Total + %: classificações declaradas, dimensão de cada KPI e KPIs só com o Total.
    classifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Partições novas em classificações curadas: cid → {pid: partição}.
    extensions: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    dimensions: dict[str, dict[str, str]] = field(default_factory=dict)
    map_share: dict[str, str] = field(default_factory=dict)  # KPI → categoria do mapa (%)
    total_only: list[tuple[str, str, str]] = field(default_factory=list)


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


def _reason(kpi: PanoramaKpi, info: Mapping[str, Any] | None, *, has_detail: bool = False) -> str:
    """Motivo para deixar o KPI de fora ('' se entra; com categorias, decidido depois)."""
    del has_detail  # o KPI que depende de categoria é decidido após o plano de detalhe
    if info is None or info.get("status") != "ok":
        return f"tabela não verificada na fonte ({(info or {}).get('error', 'sem verificação')})"
    if info.get("period_label") not in PERIOD_TYPES:
        return f"períodos por {info.get('period_label')}: tipo ainda não suportado na Gold"
    if info.get("base_level") not in SUPPORTED_LEVELS:
        return f"dados no nível {info.get('base_level')}: a Gold ainda não tem esse nível"
    return ""


def _level_counts(info: Mapping[str, Any], descriptor: Mapping[str, Any] | None) -> dict[str, int]:
    """Territórios por nível: os da verificação; sem eles (Total ".."), os do descritor."""
    counts = {lv: int(n) for lv, n in (info.get("levels") or {}).items() if n}
    if counts:
        return counts
    return {
        f"n{lvl['Id']}": int(lvl.get("QuantidadeUnidadesAtivas") or 0)
        for lvl in (descriptor or {}).get("NiveisTerritoriais") or []
        if lvl.get("QuantidadeUnidadesAtivas")
    }


def _levels(info: Mapping[str, Any]) -> list[str]:
    levels = info.get("levels") or {}
    return [lv for lv in SUPPORTED_LEVELS if levels.get(lv)]


def _rows_per_period(info: Mapping[str, Any], levels: list[str]) -> int:
    counts = info.get("levels") or {}
    rows = 0
    for lv in levels:
        found = int(counts.get(lv) or 0)
        if lv == "n6" and found < FULL_MUNICIPAL:
            rows += found + max(5, found // 5)  # recorte municipal, com folga
        else:
            rows += MAX_ROWS_PER_LEVEL[lv]
    return rows


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


DETAIL_LEVELS = ("n1", "n2", "n3")
DETAIL_LIMIT = 45_000  # margem sob o limite de 50.000 valores por requisição
# Categorias no nível municipal só em tabelas com poucos períodos (os Censos):
# cada consulta municipal com categorias leva de 60 a 120 s na fonte.
MAX_MUNICIPAL_DETAIL_UNITS = 3


@dataclass
class CuratedClassification:
    """Classificação já declarada no catálogo curado."""

    total: str
    declared: frozenset[str]
    partitions: dict[str, tuple[str, frozenset[str]]]  # id → (pai, categorias)


@dataclass
class Detail:
    """Plano de detalhe de um KPI: a classificação principal com as categorias."""

    cid: str  # "c782"
    name: str
    total: str
    categories: list[str]  # todas, com o Total primeiro
    edges: dict[str, list[str]]  # pai → filhos, na ordem do descritor
    summable: bool
    partition: str = ""  # partição mostrada no portal (filhos do Total)
    levels: tuple[str, ...] = ()  # níveis com detalhe (vazio: todos)


def _tree(categories: list[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Pai → filhos pela indentação oficial (``NivelIdentacao``)."""
    edges: dict[str, list[str]] = {}
    stack: list[tuple[int, str]] = []
    for cat in categories:
        level, cat_id = int(cat.get("NivelIdentacao") or 0), str(cat["Id"])
        while stack and stack[-1][0] >= level:
            stack.pop()
        if stack:
            edges.setdefault(stack[-1][1], []).append(cat_id)
        stack.append((level, cat_id))
    return edges


def plan_detail(  # noqa: PLR0911 - um retorno por motivo de ficar só com o Total
    kpi: PanoramaKpi,
    info: Mapping[str, Any],
    descriptor: Mapping[str, Any] | None,
) -> tuple[Detail | None, str]:
    """Classificação principal com Total, ou o motivo para ficar só com o Total."""
    classes: list[Mapping[str, Any]] = (descriptor or {}).get("Classificacoes") or []
    if not classes:
        return None, "tabela sem classificações"
    if kpi.dimensao:
        main = next((c for c in classes if f"c{c['Id']}" == kpi.dimensao), None)
        if main is None:
            return None, f"dimensão {kpi.dimensao} não existe na tabela"
    else:
        subject = [c for c in classes if c.get("Nome") not in COMMON_FILTERS]
        main = (subject or classes)[0]
    cats: list[Mapping[str, Any]] = main.get("Categorias") or []
    level0 = min((int(c.get("NivelIdentacao") or 0) for c in cats), default=0)
    top = [c for c in cats if int(c.get("NivelIdentacao") or 0) == level0]
    named_total = [c for c in top if c.get("Nome") == "Total"]
    edges = _tree(cats)
    if named_total:
        total = str(named_total[0]["Id"])
        siblings = [str(c["Id"]) for c in top if str(c["Id"]) != total]
        if siblings and not edges.get(total):
            edges[total] = siblings  # Total no mesmo nível das categorias (lista plana)
    elif len(top) == 1:
        total = str(top[0]["Id"])  # agregado único da tabela (ex.: "15 anos ou mais")
    else:
        cname = f"c{main['Id']} {main['Nome']}"
        reference = kpi.referencia.get(f"c{main['Id']}")
        if reference is not None:
            return None, f"{cname} sem Total: valor de referência {reference}"
        return None, f"{cname} sem categoria Total (requer categoria de referência)"
    observed = {c["label"]: c["categories"][0]["id"] for c in info.get("classifications") or []}
    if observed.get(str(main["Nome"])) not in (total, None, "0"):
        return None, f"c{main['Id']}: Total do descritor ({total}) difere do observado"
    if not edges.get(total):
        return None, f"c{main['Id']} sem categorias abaixo do Total"
    return (
        Detail(
            cid=f"c{main['Id']}",
            name=str(main["Nome"]),
            total=total,
            categories=[str(c["Id"]) for c in cats],
            edges=edges,
            summable=bool(main.get("CategoriasPodemSerSomadas")),
        ),
        "",
    )


def _class_id(descriptor: Mapping[str, Any] | None, label: str) -> str:
    """Código da classificação (sem o "c") pelo nome, no descritor."""
    for c in (descriptor or {}).get("Classificacoes") or []:
        if c.get("Nome") == label:
            return str(c["Id"])
    return ""


def fixed_categories(
    info: Mapping[str, Any],
    descriptor: Mapping[str, Any] | None,
    exclude: str | None,
    references: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Categoria fixa de cada classificação (exceto a dimensão principal).

    O Total que a API devolve por padrão; sem ele, o "Total" ou a única categoria
    do topo da hierarquia do descritor, pedida explicitamente. Devolve (fixas,
    parâmetros ``cNNN``, classificações sem categoria única).
    """
    by_name = {str(c["Nome"]): c for c in (descriptor or {}).get("Classificacoes") or []}
    fixed: dict[str, str] = {}
    params: dict[str, str] = {}
    missing: list[str] = []
    for cls in info.get("classifications") or []:
        label = cls["label"]
        if label == exclude:
            continue
        default = cls["categories"][0] if len(cls.get("categories") or []) == 1 else None
        if default is not None and default.get("name"):
            fixed[label] = default["id"]
            continue
        desc = by_name.get(label)
        cats: list[Mapping[str, Any]] = (desc or {}).get("Categorias") or []
        reference = (references or {}).get(f"c{desc['Id']}") if desc else None
        if reference is not None:
            if reference not in {str(c["Id"]) for c in cats}:
                missing.append(f"{label} (referência {reference} inexistente)")
                continue
            fixed[label] = reference
            params[f"c{desc['Id']}"] = reference  # type: ignore[index]
            continue
        level0 = min((int(c.get("NivelIdentacao") or 0) for c in cats), default=0)
        top = [c for c in cats if int(c.get("NivelIdentacao") or 0) == level0]
        single = [c for c in top if c.get("Nome") == "Total"] or (top if len(top) == 1 else [])
        if desc is None or not single:
            missing.append(label)
            continue
        fixed[label] = str(single[0]["Id"])
        params[f"c{desc['Id']}"] = str(single[0]["Id"])
    return fixed, params, missing


def _register(
    gen: Generated,
    detail: Detail,
    table: str,
    curated: Mapping[str, CuratedClassification],
) -> str:
    """Declara a classificação (ou usa a curada) e escolhe a partição do portal.

    Devolve "" ou o motivo do conflito. Partições: uma por categoria-pai; tabelas
    com os mesmos filhos reaproveitam a partição, e filhos diferentes que se
    sobrepõem são conflito (uma categoria fica em uma só partição).
    """
    if detail.cid in curated:
        return _register_curated(gen, detail, table, curated[detail.cid])
    entry = gen.classifications.setdefault(
        detail.cid,
        {"name": detail.name, "total": detail.total, "partitions": {}, "member": {}},
    )
    if entry["total"] != detail.total or entry["name"] != detail.name:
        return f"{detail.cid}: Total ou nome diferente entre tabelas"
    planned: dict[str, tuple[str, list[str]]] = {}
    for parent, children in detail.edges.items():
        found = {entry["member"].get(c) for c in children} - {None}
        if not found:
            pid = f"p{parent}" if f"p{parent}" not in entry["partitions"] else f"p{parent}_t{table}"
            planned[pid] = (parent, children)
        elif len(found) == 1:
            pid = found.pop()
            if set(entry["partitions"][pid]["categories"]) != set(children):
                return f"{detail.cid}: categorias de {parent} diferem de outra tabela"
        else:
            return f"{detail.cid}: categorias de {parent} em partições diferentes"
    for pid, (parent, children) in planned.items():
        entry["partitions"][pid] = {
            "parent": parent,
            "categories": children,
            "summable": detail.summable,
        }
        for c in children:
            entry["member"][c] = pid
    detail.partition = entry["member"][detail.edges[detail.total][0]]
    return ""


def _register_curated(
    gen: Generated, detail: Detail, table: str, cur: CuratedClassification
) -> str:
    """Classificação curada: reaproveita partições iguais e acrescenta as novas.

    Uma partição nova só entra se nenhuma das suas categorias já tiver posição na
    hierarquia curada (ou numa extensão anterior) e se o pai já tiver posição.
    """
    if cur.total != detail.total:
        return f"{detail.cid}: Total {detail.total} difere do curado ({cur.total})"
    ext = gen.extensions.setdefault(detail.cid, {})
    existing: dict[str, tuple[str, frozenset[str]]] = {
        **cur.partitions,
        **{pid: (p["parent"], frozenset(p["categories"])) for pid, p in ext.items()},
    }
    known = set(cur.declared) | {c for _, cats in existing.values() for c in cats}
    planned: dict[str, dict[str, Any]] = {}
    chosen: dict[str, str] = {}
    for parent, children in detail.edges.items():
        wanted = set(children)
        same = next(
            (pid for pid, (par, cats) in existing.items() if par == parent and cats == wanted),
            None,
        )
        if same is not None:
            chosen[parent] = same
            continue
        if any(c in known for c in children):
            return f"{detail.cid} curada: categorias de {parent} já têm outra posição"
        placed = {c for p in planned.values() for c in p["categories"]}
        if parent not in known and parent not in placed:
            return f"{detail.cid} curada: categoria-pai {parent} sem posição"
        pid = f"p{parent}_t{table}"
        planned[pid] = {"parent": parent, "categories": children, "summable": detail.summable}
        chosen[parent] = pid
    ext.update(planned)
    detail.partition = chosen[detail.total]
    return ""


def generate(  # noqa: PLR0912, PLR0915 - regras de elegibilidade em sequência, uma por KPI
    panorama: Panorama,
    verification: Mapping[str, Any],
    titles: Mapping[str, str],
    *,
    configured_tables: Mapping[str, str],
    existing_indicators: Iterable[str],
    existing_portal_kpis: Iterable[str],
    descriptors: Mapping[str, Mapping[str, Any]] | None = None,
    curated_classifications: Mapping[str, CuratedClassification] | None = None,
) -> Generated:
    """Configurações dos KPIs de Total elegíveis.

    ``configured_tables`` (tabela → dataset) são as tabelas já configuradas em
    arquivos curados: os KPIs delas ficam de fora (a ligação é manual).
    ``descriptors`` (tabela → ``/DescritoresTabela``) dão a aditividade, a fonte
    e as notas oficiais; sem descritor, o indicador fica não aditivo.
    """
    descriptors = descriptors or {}
    curated = curated_classifications or {}
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
        descriptor = descriptors.get(kpi.tabela)
        detail: Detail | None = None
        why_total = ""
        if info is not None and info.get("status") == "ok":
            detail, why_total = plan_detail(kpi, info, descriptor)
        reason = _reason(kpi, info, has_detail=detail is not None)
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
        info = {**info, "levels": _level_counts(info, descriptor)}
        levels = _levels(info)
        if not levels:
            out.skipped.append((kpi.id, kpi.tabela, "nenhum nível Brasil, Região, UF ou Município"))
            continue
        dataset_id = f"ibge-sidra-{kpi.tabela}"
        fact_id = f"fact_sidra_{kpi.tabela}"
        fixed, fixed_params, missing = fixed_categories(
            info, descriptor, detail.name if detail else None, kpi.referencia
        )
        if missing:
            where = ", ".join(missing)
            reason = f"sem categoria Total em: {where} (requer categoria de referência)"
            out.skipped.append((kpi.id, kpi.tabela, reason))
            continue
        period_type, per_year = PERIOD_TYPES[info["period_label"]]
        rows = _rows_per_period(info, levels) * per_year
        if rows > SIDRA_VALUE_LIMIT:
            out.skipped.append(
                (kpi.id, kpi.tabela, f"{rows} valores por requisição: exige divisão manual")
            )
            continue
        detail_params: dict[str, Any] = {}
        if detail is not None:
            n_detail = len(detail.categories) - 1
            full = rows * (n_detail + 1)
            partial = _rows_per_period(info, [lv for lv in levels if lv in DETAIL_LEVELS])
            partial *= n_detail * per_year
            units = len(
                {p[:4] for p in info.get("periods") or []}
                if per_year > 1
                else info.get("periods") or []
            )
            municipal = "n6" in levels and units > MAX_MUNICIPAL_DETAIL_UNITS
            if full <= DETAIL_LIMIT and not municipal:
                detail.levels = ()
            elif partial <= DETAIL_LIMIT and any(lv in DETAIL_LEVELS for lv in levels):
                detail.levels = tuple(lv for lv in levels if lv in DETAIL_LEVELS)
            else:
                why_total = f"{detail.cid}: {partial} valores por requisição mesmo sem municípios"
                detail = None
        if detail is not None:
            conflict = _register(out, detail, kpi.tabela, curated)
            if conflict:
                why_total, detail = conflict, None
                # Sem a dimensão, ela também fica fixa no Total.
                fixed, fixed_params, missing = fixed_categories(
                    info, descriptor, None, kpi.referencia
                )
                if missing:
                    where = ", ".join(missing)
                    reason = f"sem categoria Total em: {where} ({why_total})"
                    out.skipped.append((kpi.id, kpi.tabela, reason))
                    continue
        if detail is None and kpi.requer_categoria:
            out.skipped.append(
                (kpi.id, kpi.tabela, f"o Total é só o universo da tabela; {why_total}")
            )
            continue
        if detail is not None:
            if detail.levels:
                detail_params = {
                    "classifications": {**fixed_params, detail.cid: ",".join(detail.categories)},
                    "detail_classification": detail.cid,
                    "detail_total": detail.total,
                    "detail_levels": list(detail.levels),
                }
                rows = max(rows, partial)
            else:
                detail_params = {"classifications": {**fixed_params, detail.cid: "all"}}
                rows = full
        else:
            if fixed_params:
                detail_params = {"classifications": fixed_params}
            if why_total:
                out.total_only.append((kpi.id, kpi.tabela, why_total))
        title = titles[kpi.tabela]
        fonte = (descriptor or {}).get("Fonte")
        names = {
            str(c["Nome"]): {str(x["Id"]): str(x["Nome"]) for x in c.get("Categorias") or []}
            for c in (descriptor or {}).get("Classificacoes") or []
        }
        at = "; ".join(
            f"{label}: {names.get(label, {}).get(cat, cat)}" for label, cat in fixed.items()
        )
        reference_notes = [
            f"Valor de referência em {label}: {names.get(label, {}).get(cat, cat)} "
            "(a classificação não tem Total; as categorias não se somam)."
            for label, cat in fixed.items()
            if f"c{_class_id(descriptor, label)}" in kpi.referencia
        ]
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
                "periodicity": {"mes": "mensal", "trimestre": "trimestral"}.get(
                    period_type, _periodicity(info.get("periods") or [])
                ),
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
                    **(
                        {"period_type": period_type, "group_periods_by_year": True}
                        if period_type != "ano"
                        else {}
                    ),
                    **detail_params,
                },
                "silver": {"transformer": "sidra_observation", "territorial_reference": "ibge-dtb"},
            }
        )
        territories = ", ".join(LEVEL_LABELS[lv] for lv in levels)
        grain = f"território ({territories}) x {period_type}"
        if kpi.pausado:
            # Em espera: o dataset fica nas fontes (para repescar), fora do catálogo e do portal.
            out.skipped.append((kpi.id, kpi.tabela, f"em espera: {kpi.pausado}"))
            continue
        fact: dict[str, Any] = {
            "id": fact_id,
            "dataset": dataset_id,
            "grain": grain + (f" x {detail.name.lower()}" if detail else ""),
            "description": (
                f"{kpi.label}: tabela SIDRA {kpi.tabela} ({title}), "
                + (f"por {detail.name.lower()}." if detail else "no Total.")
            ),
        }
        if detail is not None:
            fact["classifications"] = {detail.cid: f"{detail.cid}_category_key"}
        fact["fixed_categories"] = fixed
        out.facts.append(fact)
        caveats = [*reference_notes, *_caveats(kpi, info, levels, descriptor)]
        if detail is not None and detail.levels:
            shown = ", ".join(LEVEL_LABELS[lv] for lv in detail.levels)
            caveats.insert(
                0,
                f"As categorias de {detail.name} vêm até {shown}; nos municípios, só o Total "
                "(a série municipal por categoria exigiria milhares de consultas à fonte).",
            )
        if detail is not None and not detail.summable:
            caveats.insert(
                0,
                f"As categorias de {detail.name} podem se sobrepor (a fonte não permite somá-las): "
                "o percentual de cada uma é em relação ao Total, e a soma pode passar de 100%.",
            )
        if detail is not None:
            out.dimensions[kpi.id] = {
                "classification": detail.cid,
                "partition": detail.partition,
                "label": detail.name,
            }
            if kpi.requer_categoria:
                # O Total é só o universo: o mapa mostra o % da categoria principal.
                out.map_share[kpi.id] = kpi.categoria_mapa or detail.edges[detail.total][0]
        out.indicators.append(
            {
                "id": kpi.id,
                "name": variable["name"],
                "description": (
                    f"{variable['name']} ({kpi.pesquisa}, tabela SIDRA {kpi.tabela}). "
                    + (f"Recorte: {at}." if at else "Tabela sem classificações.")
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
                "caveats": caveats,
                **({"first_period": kpi.periodo_inicial} if kpi.periodo_inicial else {}),
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
    """Fragmento do catálogo semântico (classificações, fatos e indicadores)."""
    lines = [GENERATED_HEADER, 'config_version = "1.0.0"', f"scope = {_value(scope)}", ""]
    for cid, entry in gen.classifications.items():
        lines += [
            "[[classifications]]",
            f"id = {_value(cid)}",
            f"name = {_value(entry['name'])}",
            f"silver_dimension = {_value(entry['name'])}",
            f"total = {_value(entry['total'])}",
            "",
        ]
        for pid, part in entry["partitions"].items():
            lines += [
                "[[classifications.partitions]]",
                f"id = {_value(pid)}",
                f"label = {_value(entry['name'])}",
            ]
            if part["parent"] != entry["total"]:
                lines.append(f"parent = {_value(part['parent'])}")
            lines += [
                f"categories = {_value(part['categories'])}",
                "exhaustive = false",
                *([] if part["summable"] else ["summable = false"]),
                "",
            ]
    for cid, parts in gen.extensions.items():
        for pid, part in parts.items():
            lines += [
                "[[classification_partitions]]",
                f"classification = {_value(cid)}",
                f"id = {_value(pid)}",
                f"label = {_value(pid)}",
                f"parent = {_value(part['parent'])}",
                f"categories = {_value(part['categories'])}",
                "exhaustive = false",
                *([] if part["summable"] else ["summable = false"]),
                "",
            ]
    for fact in gen.facts:
        lines += _table("facts", fact)
    for ind in gen.indicators:
        lines += _table("indicators", ind)
    return "\n".join(lines).rstrip() + "\n"


def render_portal(gen: Generated, scope: str) -> str:
    """Fragmento do portal: temas e subtemas do panorama, KPIs com o id do item."""
    order = list(dict.fromkeys(d["classification"] for d in gen.dimensions.values()))
    lines = [GENERATED_HEADER, 'config_version = "1.0.0"', f"scope = {_value(scope)}"]
    if order:
        lines.append(f"dimension_order = {_value(order)}")
    lines.append("")
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
        ]
        dim = gen.dimensions.get(kpi.id)
        if dim:
            lines.append(f"dimensions = [{_value(dim)}]")
        if kpi.id in gen.map_share:
            lines.append(f"map_share = {_value(gen.map_share[kpi.id])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_report(gen: Generated) -> str:
    """Resumo em texto: gerados e deixados de fora, com o motivo."""
    lines = [
        f"{len(gen.indicators)} KPIs gerados ({len(gen.datasets)} tabelas), "
        f"{len(gen.dimensions)} com categorias (Total + %)."
    ]
    if gen.total_only:
        lines.append(f"{len(gen.total_only)} KPIs só com o Total:")
        lines += [f"  {kpi} ({table}): {why}" for kpi, table, why in gen.total_only]
    if gen.skipped:
        lines.append(f"{len(gen.skipped)} KPIs planejados ficaram de fora:")
        lines += [f"  {kpi} ({table}): {why}" for kpi, table, why in gen.skipped]
    return "\n".join(lines)


# ------------------------------------------------------------------ proposta Total + %

# Classificações que são recortes comuns (filtros), e não o assunto do KPI.
COMMON_FILTERS = {
    "Sexo",
    "Situação do domicílio",
    "Grupo de idade",
    "Grupos de idade",
    "Idade",
    "Cor ou raça",
    "Classe de tamanho da população do município",
    "Localização do domicílio",
    "Referência temporal",
    # Recortes técnicos ou de calendário, que não são o assunto do KPI.
    "Forma de declaração da idade",
    "Mês de ocorrência",
    "Tipo de inspeção",
}
MAX_LISTED = 8


def _top_categories(classification: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Categorias do primeiro nível abaixo do Total (ou do nível mais alto, sem Total)."""
    cats: list[Mapping[str, Any]] = classification.get("Categorias") or []
    if not cats:
        return []
    top = min(int(c.get("NivelIdentacao") or 0) for c in cats)
    has_total = bool(classification.get("CategoriasPermitemObterTotal")) and any(
        int(c.get("NivelIdentacao") or 0) == top and c.get("Nome") == "Total" for c in cats
    )
    level = top + 1 if has_total else top
    return [c for c in cats if int(c.get("NivelIdentacao") or 0) == level]


def propose_dimensions(
    panorama: Panorama, descriptors: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Dimensão principal proposta para cada KPI (onda Total + %), a partir dos descritores.

    A dimensão principal é a primeira classificação que não é um recorte comum
    (sexo, idade, cor ou raça, situação do domicílio...). Sem ela, o primeiro
    recorte comum. As categorias listadas são as do primeiro nível da hierarquia.
    """
    out = []
    for theme, _sub, kpi in panorama.items():
        desc = descriptors.get(kpi.tabela) or {}
        classes: list[Mapping[str, Any]] = desc.get("Classificacoes") or []
        subject = [c for c in classes if c.get("Nome") not in COMMON_FILTERS]
        candidates = subject or classes
        main: Mapping[str, Any] | None = candidates[0] if candidates else None
        others = [c for c in classes if c is not main]
        row: dict[str, Any] = {
            "theme": theme.label,
            "kpi": kpi.id,
            "label": kpi.label,
            "table": kpi.tabela,
            "classification": None,
            "categories": [],
            "sums": None,
            "has_total": None,
            "others": [f"c{c['Id']} {c['Nome']}" for c in others],
        }
        if main is not None:
            top = _top_categories(main)
            row |= {
                "classification": f"c{main['Id']} {main['Nome']}",
                "categories": [str(c.get("Nome")) for c in top],
                "sums": bool(main.get("CategoriasPodemSerSomadas")),
                "has_total": bool(main.get("CategoriasPermitemObterTotal")),
                "is_subject": bool(subject),
            }
        out.append(row)
    return out


def render_proposal(rows: list[dict[str, Any]], published: set[str]) -> str:
    """Proposta em Markdown, para aprovação do mantenedor."""
    lines = [
        "# Proposta: dimensão principal de cada KPI (onda Total + %)",
        "",
        "<!-- Gerado por `odb panorama propor`; não editar à mão. -->",
        "",
        "Regra do mantenedor (ADR-0010): o KPI é o Total; as categorias da dimensão "
        "principal aparecem como % do Total; as demais dimensões ficam no Total.",
        "",
        "A proposta vem dos descritores oficiais (`configs/catalog/descritores/`). A "
        "dimensão principal é a primeira classificação que não é um recorte comum "
        "(sexo, idade, cor ou raça, situação do domicílio, tamanho do município, "
        "localização, referência temporal). Os recortes comuns seguem como filtros. "
        "**Soma** diz se o IBGE permite somar as categorias (`CategoriasPodemSerSomadas`); "
        "sem soma, o % não é uma partição do Total e o portal mostra o valor de cada "
        "categoria. Para aprovar ou trocar uma linha, basta indicar a tabela e a "
        "classificação desejada.",
        "",
        "| Tema | KPI | Tabela | Estado | Dimensão principal | Categorias (1º nível) | Soma | "
        "Outras classificações |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        cats = r["categories"]
        listed = "; ".join(cats[:MAX_LISTED]) + (
            f"; … (+{len(cats) - MAX_LISTED})" if len(cats) > MAX_LISTED else ""
        )
        dim = r["classification"] or "— (só o Total)"
        if r["classification"] and not r.get("is_subject"):
            dim += " *(recorte comum)*"
        sums = "—" if r["sums"] is None else ("sim" if r["sums"] else "não")
        if r["has_total"] is False:
            sums += " (sem Total)"
        cells = [
            r["theme"],
            r["label"],
            f"[{r['table']}](https://sidra.ibge.gov.br/tabela/{r['table']})",
            "publicado (Total)" if r["kpi"] in published else "pendente",
            dim,
            listed or "—",
            sums,
            "; ".join(r["others"]) or "—",
        ]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(lines) + "\n"
