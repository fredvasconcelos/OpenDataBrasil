"""Comandos `odb panorama`: taxonomia do portal e Tier 1 (ADR-0010)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer

from odb_cli.panorama_gen import (
    CuratedClassification,
    Generated,
    generate,
    propose_dimensions,
    render_indicators,
    render_portal,
    render_proposal,
    render_report,
    render_sources,
)
from odb_common.logging import configure_logging
from odb_common.settings import Settings, load_settings
from odb_ingestion import HttpClient, load_sources
from odb_ingestion.connectors.sidra_probe import probe_table
from odb_ingestion.http import HttpError
from odb_semantics import (
    Panorama,
    check_against_acervo,
    check_against_portal,
    load_catalog,
    load_panorama,
    resolve_links,
)

panorama_app = typer.Typer(no_args_is_help=True, help="Panorama do Brasil (temas e Tier 1).")

DEFAULT_PANORAMA = Path("configs/catalog/panorama.toml")
DEFAULT_PORTAL_DIR = Path("configs/portal")
DEFAULT_SCOPE = "demografia"
GENERATED_NAME = "panorama.toml"
GENERATED_SOURCES = "ibge-panorama.toml"
DESCRIPTORS_DIR = "descritores"
DEFAULT_DOC = Path("docs/data_catalog/panorama-tier1.md")
LEVEL_NAMES = {"n1": "Brasil", "n2": "Região", "n3": "UF", "n7": "RM", "n6": "Município"}
# Último período antes do qual a série é sinalizada como antiga no catálogo.
OLD_SERIES_YEAR = 2015
SIDRA_SOURCE = "ibge-sidra"
# Substituível em testes para simular a fonte sem acesso à rede.
HTTP_TRANSPORT: httpx.BaseTransport | None = None


def _settings() -> Settings:
    settings = load_settings()
    configure_logging(settings.log_level)
    return settings


def _portal_kpis(portal_dir: Path, scope: str, exclude: str | None = None) -> dict[str, Any]:
    """KPIs do portal do escopo: arquivo principal e fragmentos (``<escopo>/*.toml``)."""
    import tomllib  # noqa: PLC0415 - só estes comandos leem o portal

    fragments = [f for f in sorted((portal_dir / scope).glob("*.toml")) if f.name != exclude]
    paths = [portal_dir / f"{scope}.toml", *fragments]
    out: dict[str, Any] = {}
    for path in paths:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for t in data.get("themes", []):
            for s in t["subthemes"]:
                for k in s["kpis"]:
                    out[k["id"]] = k
    return out


def _published(config: Panorama, portal_kpis: dict[str, Any]) -> set[str]:
    return {item for item, link in resolve_links(config, portal_kpis).items() if link}


@panorama_app.command("validar")
def validar(
    panorama: Annotated[Path, typer.Option(help="Arquivo do panorama.")] = DEFAULT_PANORAMA,
    portal_dir: Annotated[Path, typer.Option(help="Diretório do portal.")] = DEFAULT_PORTAL_DIR,
    escopo: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
) -> None:
    """Confere a estrutura, o snapshot do acervo e a ligação com os KPIs do portal."""
    config = load_panorama(panorama)
    titles = check_against_acervo(config, panorama.parent / config.acervo)
    portal = _portal_kpis(portal_dir, escopo)
    check_against_portal(config, portal)
    items = config.items()
    published = len(_published(config, portal))
    typer.echo(
        f"panorama {config.config_version}: {len(config.temas)} temas, "
        f"{len(config.subthemes())} subtemas, {len(items)} KPIs "
        f"({published} publicados, {len(items) - published} planejados), "
        f"{len(titles)} tabelas conferidas no acervo de {config.acervo_obtido_em}"
    )


def _generation(config: Panorama, panorama: Path, raiz: Path, escopo: str) -> Generated:
    """KPIs de Total gerados e deixados de fora, sem gravar nada.

    Considera só a configuração curada: o fragmento gerado é ignorado na leitura.
    """
    import tomllib  # noqa: PLC0415

    titles = check_against_acervo(config, panorama.parent / config.acervo)
    data = json.loads((panorama.parent / "panorama_verificacao.json").read_text("utf-8"))
    if data.get("acervo_sha256") != config.acervo_sha256:
        typer.echo("a verificação é de outro snapshot do acervo: rode `verificar`", err=True)
        raise typer.Exit(code=2)
    configured: dict[str, str] = {}
    for path in sorted((raiz / "sources").glob("*.toml")):
        if path.name == GENERATED_SOURCES:
            continue
        for ds in tomllib.loads(path.read_text(encoding="utf-8")).get("datasets", []):
            table = ds.get("params", {}).get("table")
            if ds.get("source") == "ibge-sidra" and table:
                configured[str(table)] = ds["id"]
    indicators_dir = raiz / "indicators"
    fragments = [
        f for f in sorted((indicators_dir / escopo).glob("*.toml")) if f.name != GENERATED_NAME
    ]
    curated = load_catalog(indicators_dir / f"{escopo}.toml", fragments)
    curated_classes = {
        c.id: CuratedClassification(
            total=c.total,
            declared=c.declared(),
            partitions={
                part.id: (c.parent_of(part), frozenset(part.categories)) for part in c.partitions
            },
        )
        for c in curated.classifications
    }
    portal = _portal_kpis(raiz / "portal", escopo, exclude=GENERATED_NAME)
    descriptors = {
        path.stem[1:]: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((panorama.parent / DESCRIPTORS_DIR).glob("t*.json"))
    }
    return generate(
        config,
        data,
        titles,
        configured_tables=configured,
        existing_indicators=[i.id for i in curated.indicators],
        existing_portal_kpis=list(portal),
        descriptors=descriptors,
        curated_classifications=curated_classes,
    )


@panorama_app.command("gerar")
def gerar(
    panorama: Annotated[Path, typer.Option(help="Arquivo do panorama.")] = DEFAULT_PANORAMA,
    escopo: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    raiz: Annotated[Path, typer.Option(help="Raiz dos diretórios configs/.")] = Path("configs"),
) -> None:
    """Gera fontes, catálogo e portal dos KPIs de Total do panorama (fragmentos)."""
    config = load_panorama(panorama)
    gen = _generation(config, panorama, raiz, escopo)
    targets = {
        raiz / "sources" / GENERATED_SOURCES: render_sources(gen),
        raiz / "indicators" / escopo / GENERATED_NAME: render_indicators(gen, escopo),
        raiz / "portal" / escopo / GENERATED_NAME: render_portal(gen, escopo),
    }
    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    typer.echo(render_report(gen))
    typer.echo("gravados: " + ", ".join(str(p) for p in targets))


@panorama_app.command("propor")
def propor(
    panorama: Annotated[Path, typer.Option(help="Arquivo do panorama.")] = DEFAULT_PANORAMA,
    escopo: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    raiz: Annotated[Path, typer.Option(help="Raiz dos diretórios configs/.")] = Path("configs"),
    saida: Annotated[Path, typer.Option(help="Markdown de saída.")] = Path(
        "docs/data_catalog/panorama-proposta-categorias.md"
    ),
) -> None:
    """Propõe a dimensão principal de cada KPI (onda Total + %), a partir dos descritores."""
    config = load_panorama(panorama)
    descriptors = {
        path.stem[1:]: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((panorama.parent / DESCRIPTORS_DIR).glob("t*.json"))
    }
    live = _published(config, _portal_kpis(raiz / "portal", escopo))
    saida.write_text(render_proposal(propose_dimensions(config, descriptors), live), "utf-8")
    typer.echo(f"proposta gravada em {saida}")


@panorama_app.command("descrever")
def descrever(
    panorama: Annotated[Path, typer.Option(help="Arquivo do panorama.")] = DEFAULT_PANORAMA,
    tabela: Annotated[list[str] | None, typer.Option(help="Só estas tabelas (repetível).")] = None,
    retomar: Annotated[bool, typer.Option(help="Não baixa de novo os já gravados.")] = False,
) -> None:
    """Grava o descritor oficial (``/DescritoresTabela``) de cada tabela do panorama.

    O descritor traz variáveis (unidade e se somam entre territórios),
    classificações com códigos, categorias e indentação, níveis territoriais,
    períodos, notas e fonte. A resposta é gravada sem alteração, com o
    SHA-256 no índice ``descritores/indice.json``.
    """
    import hashlib  # noqa: PLC0415

    settings = _settings()
    config = load_panorama(panorama)
    check_against_acervo(config, panorama.parent / config.acervo)
    unknown = sorted(set(tabela or ()) - set(config.tables()))
    if unknown:
        typer.echo(f"tabelas fora do panorama: {unknown}", err=True)
        raise typer.Exit(code=2)
    tables = [t for t in config.tables() if not tabela or t in tabela]
    source = load_sources(settings.sources_config_dir).sources[SIDRA_SOURCE]
    out_dir = panorama.parent / DESCRIPTORS_DIR
    out_dir.mkdir(exist_ok=True)
    index_path = out_dir / "indice.json"
    index: dict[str, Any] = (
        json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    )
    failed = 0
    with HttpClient(source.http, transport=HTTP_TRANSPORT) as http:
        for i, table in enumerate(tables, 1):
            target = out_dir / f"t{table}.json"
            if retomar and target.exists() and index.get(table, {}).get("status") == "ok":
                continue
            url = source.base_url.rstrip("/") + f"/DescritoresTabela/t/{table}"
            entry: dict[str, Any] = {"url": url, "retrieved_at": datetime.now(UTC).isoformat()}
            try:
                body = http.get_bytes(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or str(payload.get("Id")) != table:
                    got = payload.get("Id") if isinstance(payload, dict) else "?"
                    msg = f"descritor inesperado: Id {got}"
                    raise ValueError(msg)
                target.write_bytes(body)
                entry |= {
                    "status": "ok",
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "size_bytes": len(body),
                }
            except (HttpError, ValueError) as exc:
                entry |= {"status": "erro", "error": str(exc)[:300]}
                failed += 1
            index[table] = entry
            index_path.write_text(
                json.dumps(dict(sorted(index.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n",
                encoding="utf-8",
            )
            typer.echo(f"[{i:3}/{len(tables)}] {table:>6} {entry['status']}")
    typer.echo(f"{len(tables)} descritores em {out_dir} ({failed} com erro)")
    if failed:
        raise typer.Exit(code=1)


@panorama_app.command("verificar")
def verificar(
    panorama: Annotated[Path, typer.Option(help="Arquivo do panorama.")] = DEFAULT_PANORAMA,
    saida: Annotated[Path | None, typer.Option(help="JSON de saída.")] = None,
    tabela: Annotated[list[str] | None, typer.Option(help="Só estas tabelas (repetível).")] = None,
    retomar: Annotated[
        bool, typer.Option(help="Mantém as tabelas já verificadas com sucesso na saída.")
    ] = False,
) -> None:
    """Consulta na API SIDRA os metadados (Totais) de cada tabela do panorama.

    Só tabelas do acervo oficial; ritmo e tentativas da fonte ``ibge-sidra``.
    O resultado é gravado após cada tabela, para permitir retomar.
    """
    settings = _settings()
    config = load_panorama(panorama)
    titles = check_against_acervo(config, panorama.parent / config.acervo)
    out = saida or panorama.parent / "panorama_verificacao.json"
    tables = [t for t in config.tables() if not tabela or t in tabela]
    unknown = sorted(set(tabela or ()) - set(config.tables()))
    if unknown:
        typer.echo(f"tabelas fora do panorama: {unknown}", err=True)
        raise typer.Exit(code=2)
    source = load_sources(settings.sources_config_dir).sources[SIDRA_SOURCE]
    previous: dict[str, Any] = {}
    if retomar and out.exists():
        previous = {
            t["table"]: t
            for t in json.loads(out.read_text(encoding="utf-8")).get("tables", [])
            if t.get("status") == "ok"
        }
    results: dict[str, Any] = dict(previous)
    started = datetime.now(UTC).isoformat()

    def save() -> None:
        ordered = [results[t] for t in config.tables() if t in results]
        payload = {
            "panorama_version": config.config_version,
            "acervo": config.acervo,
            "acervo_sha256": config.acervo_sha256,
            "source_id": SIDRA_SOURCE,
            "base_url": source.base_url,
            "started_at": started,
            "updated_at": datetime.now(UTC).isoformat(),
            "tables": ordered,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    failed = 0
    with HttpClient(source.http, transport=HTTP_TRANSPORT) as http:
        for i, table in enumerate(tables, 1):
            if table in previous:
                continue
            probe = probe_table(http, source.base_url, table)
            record = {
                "title": titles[table],
                "checked_at": datetime.now(UTC).isoformat(),
                **asdict(probe),
            }
            results[table] = record
            failed += probe.status != "ok"
            save()
            typer.echo(f"[{i:3}/{len(tables)}] {table:>6} {probe.status:4} {probe.error or ''}")
    save()
    typer.echo(f"{len(results)} tabelas em {out} ({failed} com erro nesta execução)")
    if failed:
        raise typer.Exit(code=1)


def _periods(info: dict[str, Any]) -> str:
    periods = info.get("periods") or []
    if not periods:
        return "—"
    span = periods[0] if len(periods) == 1 else f"{periods[0]}\u2013{periods[-1]}"
    return f"{info.get('period_label') or 'Período'} {span} ({len(periods)})"


def _levels(info: dict[str, Any]) -> str:
    levels = info.get("levels") or {}
    found = [
        f"{LEVEL_NAMES[k]} ({levels[k]})" if k in ("n6", "n7") else LEVEL_NAMES[k]
        for k in LEVEL_NAMES
        if levels.get(k)
    ]
    return ", ".join(found) or "—"


def _flags(info: dict[str, Any] | None) -> list[str]:
    if info is None:
        return ["não verificada"]
    if info.get("status") != "ok":
        return [f"não verificada: {info.get('error')}"]
    flags = []
    levels = info.get("levels") or {}
    base_level = info.get("base_level") or ""
    # Sem a classificação na consulta, a API devolve a categoria-padrão. Quando a
    # classificação não tem Total, vem a categoria "0" sem nome e o valor ".."
    # ("não se aplica", na legenda oficial do SIDRA).
    no_total = [
        c["label"]
        for c in info.get("classifications") or []
        if any(cat.get("id") == "0" and not cat.get("name") for cat in c.get("categories") or [])
    ]
    if no_total:
        flags.append(f"sem categoria Total em: {', '.join(no_total)} (exige escolher categoria)")
    elif not any(levels.values()):
        flags.append("Total sem valor informativo")
    elif not levels.get("n1"):
        flags.append(f"sem nível Brasil (base: {LEVEL_NAMES.get(base_level, '?')})")
    last = (info.get("periods") or [""])[-1][:4]
    if last.isdigit() and int(last) < OLD_SERIES_YEAR:
        flags.append(f"último período {last}")
    for c in info.get("classifications") or []:
        if len(c.get("categories") or []) > 1:
            flags.append(f"{c['label']}: sem categoria Total única")
        elif c.get("categories") and c["categories"][0].get("name") not in ("Total", "", None):
            flags.append(f"{c['label']}: categoria-padrão '{c['categories'][0]['name']}'")
    if not info.get("periods_complete", True):
        flags.append("períodos lidos pela 1ª variável (excesso de valores)")
    return flags


def render_catalog(
    config: Panorama,
    titles: dict[str, str],
    verification: dict[str, Any] | None,
    published_ids: set[str] | None = None,
    reasons: dict[str, str] | None = None,
) -> str:
    """Catálogo em Markdown do panorama, com os metadados verificados na fonte.

    ``published_ids``: itens com KPI no portal (por padrão, os que têm ``kpi``).
    """
    tables = {t["table"]: t for t in (verification or {}).get("tables", [])}
    items = config.items()
    live = (
        published_ids
        if published_ids is not None
        else {k.id for _, _, k in items if k.kpi is not None}
    )
    published = len(live)
    checked = sum(1 for t in config.tables() if tables.get(t, {}).get("status") == "ok")
    lines = [
        "# Panorama do Brasil: temas, subtemas e KPIs do Tier 1",
        "",
        "<!-- Gerado por `odb panorama documentar`; não editar à mão. -->",
        "",
        "Regra e decisões: [ADR-0010](../adr/0010-panorama-taxonomia-e-tier1.md). "
        "Fonte da lista: `configs/catalog/panorama.toml` "
        f"(versão {config.config_version}), conferida contra o acervo SIDRA exportado em "
        f"{config.acervo_obtido_em} (`{config.acervo}`).",
        "",
        f"- {len(config.temas)} temas, {len(config.subthemes())} subtemas, {len(items)} KPIs "
        f"de {len(config.tables())} tabelas;",
        f"- {published} KPIs publicados no portal e {len(items) - published} em preparação;",
    ]
    if verification:
        lines.append(
            f"- {checked} de {len(config.tables())} tabelas verificadas na API SIDRA "
            f"(`panorama_verificacao.json`, atualizado em {verification.get('updated_at', '?')})."
        )
    else:
        lines.append("- metadados ainda não verificados na fonte (`odb panorama verificar`).")
    lines += [
        "",
        "Colunas: **Períodos** traz o tipo, o intervalo e a quantidade; **Níveis** lista os "
        "níveis com dados no último período (RM e Município com a contagem); **Var.** é o "
        "número de variáveis da tabela.",
    ]
    for i, theme in enumerate(config.temas, 1):
        filters = ", ".join(config.filter_label(f) for f in theme.filtros) or "—"
        lines += ["", f"## {i}. {theme.label}", "", f"Filtros do tema: {filters}.", ""]
        lines += [
            "| Subtema | KPI | Tabela | Pesquisa | Filtros | Estado | Períodos | Níveis "
            "| Var. | Observações |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for sub in theme.subtemas:
            for kpi in sub.kpis:
                info = tables.get(kpi.tabela)
                notes = _flags(info) + ([kpi.nota] if kpi.nota else [])
                if kpi.id not in live and (reasons or {}).get(kpi.id):
                    notes.insert(0, f"**pendente:** {(reasons or {})[kpi.id]}")
                cells = [
                    sub.label,
                    kpi.label,
                    f"[{kpi.tabela}](https://sidra.ibge.gov.br/tabela/{kpi.tabela} "
                    f'"{titles[kpi.tabela].replace(chr(34), chr(39))}")',
                    kpi.pesquisa,
                    ", ".join(config.filter_label(f) for f in kpi.filtros) or "—",
                    "publicado" if kpi.id in live else "em preparação",
                    _periods(info or {}),
                    _levels(info or {}),
                    str(len((info or {}).get("variables") or [])) if info else "—",
                    "; ".join(notes) or "—",
                ]
                lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(lines) + "\n"


@panorama_app.command("documentar")
def documentar(
    panorama: Annotated[Path, typer.Option(help="Arquivo do panorama.")] = DEFAULT_PANORAMA,
    verificacao: Annotated[Path | None, typer.Option(help="JSON da verificação.")] = None,
    saida: Annotated[Path, typer.Option(help="Markdown de saída.")] = DEFAULT_DOC,
    escopo: Annotated[str, typer.Option(help="Escopo de publicação.")] = DEFAULT_SCOPE,
    raiz: Annotated[Path, typer.Option(help="Raiz dos diretórios configs/.")] = Path("configs"),
) -> None:
    """Gera o catálogo do Tier 1 a partir do panorama e da verificação na fonte."""
    portal_dir = raiz / "portal"
    config = load_panorama(panorama)
    titles = check_against_acervo(config, panorama.parent / config.acervo)
    source = verificacao or panorama.parent / "panorama_verificacao.json"
    data = json.loads(source.read_text(encoding="utf-8")) if source.exists() else None
    live = _published(config, _portal_kpis(portal_dir, escopo))
    reasons = {kpi: why for kpi, _, why in _generation(config, panorama, raiz, escopo).skipped}
    saida.write_text(render_catalog(config, titles, data, live, reasons), encoding="utf-8")
    typer.echo(f"catálogo gravado em {saida}")
