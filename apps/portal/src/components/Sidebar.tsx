"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { CatalogPanel } from "@/components/CatalogPanel";
import { formatPeriod } from "@/lib/format";
import { flatten, flattenPlanned, highlight, matchKpi, matchPlanned, snippet, sourceTable } from "@/lib/catalog";
import type { Geography, Kpi, KpiIndex, Navigation, PortalIndex } from "@/lib/types";
import { PeriodFilter } from "@/components/PeriodFilter";
import { canAccumulate, canIsolate, canCross, grainPeriods, timeGrains, yearsOf } from "@/lib/state";

interface Props {
  nav: Navigation | PortalIndex;
  kpi: Kpi | null;
  dimensions: string[];
  onKpi: (id: string) => void;
  onPreload?: (id: string) => void;
  municipalStates?: Geography[];
  municipalWithin?: string | null;
  onMunicipalState?: (key: string) => void;
  onMunicipalNation?: () => void;
  onDimensions: (dims: string[]) => void;
  /** Filtro do Detalhar por (DS 2.4): categorias marcadas (vazio na dimensão: todas). */
  categories?: string[];
  /** Muda dimensões e categorias juntas (marcar uma categoria liga a dimensão). */
  onDetail?: (dims: string[], categories: string[]) => void;
  /** Filtros do indicador atual (nível territorial e período). */
  level: string;
  /** Períodos marcados (ADR-0026): folhas no grão ou, com Isolar, anos. */
  selection: string[];
  /** Grão de tempo (ADR-0013): null é o publicado; os demais somam os meses. */
  grain: string | null;
  onLevel: (level: string) => void;
  onPeriods: (periods: string[]) => void;
  /** "Acumular" (ADR-0026): só em fluxos e variações %; nos demais, desabilitado. */
  accumulate?: boolean;
  onAccumulate?: (accumulate: boolean) => void;
  onGrain: (grain: string | null) => void;
  /** "Isolar período": barras por parte do ano, acumuladas entre os anos. */
  isolate?: boolean;
  onIsolate?: (isolate: boolean) => void;
  correction?: string | null;
  onCorrection?: (correction: string | null) => void;
  /** Volta os filtros ao estado inicial do indicador (desativado se já estiverem nele). */
  onClear: () => void;
  canClear: boolean;
}

// Barra lateral (Design System ODBr; DS 2.9, proposta B): no topo, o indicador atual e o
// botão "Trocar indicador" ("/"), que abre o painel do catálogo ao lado da barra; abaixo,
// os filtros (nível territorial, período e "Detalhar por"), com rolagem própria, e
// "Limpar filtros" fixo no rodapé. A árvore "Temas e indicadores" fica só no celular
// (painel inferior "Indicadores"); no desktop, o catálogo é o painel.
// A taxonomia vem do panorama (ADR-0010): KPIs ainda sem dados aparecem desativados,
// marcados "em preparação", com a tabela SIDRA de origem no title.
// Todos os filtros do portal ficam aqui; a área central só tem conteúdo e exportações.
// v2.3: busca sob "Temas e indicadores" (proposta A): filtra a árvore enquanto digita,
// marca o termo, mostra o trecho da descrição quando o achado não está no nome,
// "/" leva o foco ao campo e Esc limpa.
export function Sidebar({
  nav,
  kpi,
  dimensions,
  onKpi,
  onPreload,
  municipalStates = [],
  municipalWithin = null,
  onMunicipalState,
  onMunicipalNation,
  onDimensions,
  categories = [],
  onDetail,
  level,
  selection,
  grain,
  correction = null,
  onCorrection = () => undefined,
  onLevel,
  onPeriods,
  accumulate = false,
  onAccumulate,
  onGrain,
  isolate = false,
  onIsolate,
  onClear,
  canClear,
}: Props) {
  const t = useTranslations();
  const aside = useRef<HTMLElement>(null);
  const switcher = useRef<HTMLButtonElement>(null);
  const [panel, setPanel] = useState<{ top: number; left: number; height: number } | null>(null);
  const [periodsOpen, setPeriodsOpen] = useState(false);
  const openPanel = useCallback(() => {
    const r = aside.current?.getBoundingClientRect();
    if (!r) return;
    const top = Math.max(8, r.top + 8);
    setPanel({ top, left: r.right + 8, height: Math.max(320, Math.min(r.bottom, window.innerHeight) - top - 8) });
  }, []);
  const closePanel = useCallback(() => {
    setPanel(null);
    switcher.current?.focus();
  }, []);
  // "/" fora de campos abre o catálogo (no celular, a busca da árvore cuida do atalho).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || panel) return;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)) return;
      if (!switcher.current?.getClientRects().length) return;
      e.preventDefault();
      openPanel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [openPanel, panel]);
  const crumb = kpi
    ? nav.themes
        .flatMap((th) => th.subthemes.filter((s) => s.kpis.some((k) => k.kpi_id === kpi.kpi_id)).map((s) => `${th.label} › ${s.label}`))
        .at(0)
    : null;
  const periodSummary =
    selection.length > 1
      ? t("dashboard.periodRange", { from: formatPeriod(selection[0] ?? ""), to: formatPeriod(selection.at(-1) ?? "") })
      : selection[0]
        ? formatPeriod(selection[0])
        : "—";
  return (
    <aside className="sidebar" ref={aside}>
      <div className="sb-current">
        {kpi ? (
          <>
            {crumb ? <p className="sb-crumb">{crumb}</p> : null}
            <p className="sb-kpi">{kpi.label}</p>
          </>
        ) : null}
        <button
          ref={switcher}
          type="button"
          className="sb-switch"
          aria-haspopup="dialog"
          aria-expanded={Boolean(panel)}
          onClick={() => (panel ? closePanel() : openPanel())}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <span>{kpi ? t("dashboard.switchKpi") : t("dashboard.chooseKpi")}</span>
          <kbd aria-hidden="true">/</kbd>
        </button>
      </div>
      {panel ? <CatalogPanel nav={nav} kpi={kpi} onKpi={onKpi} onPreload={onPreload} onClose={closePanel} place={panel} /> : null}
      {kpi ? (
        <section className="filters" aria-label={t("dashboard.filters")}>
          <h2>{t("dashboard.filters")}</h2>
          <div className="filters-body">
          <label className="field">
            {t("dashboard.level")}
            <select value={level} onChange={(e) => onLevel(e.target.value)}>
              {kpi.levels.filter((l) => l !== "municipio" || !onMunicipalState || municipalWithin || level === "municipio").map((l) => (
                <option key={l} value={l}>
                  {t(`levels.${l}`)}
                  {kpi.map_levels.includes(l) ? "" : " (sem mapa)"}
                </option>
              ))}
            </select>
          </label>
          {kpi.levels.includes("municipio") && onMunicipalState ? (
            <div className="municipal-filter">
              <label className="field">
                {t("dashboard.focus.state")}
                <select value={municipalWithin ?? ""} onChange={(e) => { if (e.target.value) onMunicipalState(e.target.value); }}>
                  <option value="">{t("dashboard.focus.chooseState")}</option>
                  {municipalStates.map((geo) => <option key={geo.geography_key} value={geo.geography_key}>{geo.name}</option>)}
                </select>
              </label>
              <button type="button" className="text-btn" onClick={onMunicipalNation}>{t("dashboard.focus.nationalMunicipalities")}</button>
            </div>
          ) : null}
          {timeGrains(kpi).length > 1 || canIsolate(kpi, grain) || canAccumulate(kpi) ? (
            <fieldset className="grains">
              <legend>{t("dashboard.grain")}</legend>
              {timeGrains(kpi).map((g, i) => (
                <label key={g.grain} className="check">
                  <input
                    type="radio"
                    name="grao"
                    checked={(grain ?? timeGrains(kpi)[0]?.grain) === g.grain}
                    onChange={() => onGrain(i === 0 ? null : g.grain)}
                  />
                  {t(`grains.${g.grain}`)}
                </label>
              ))}
              {grain ? <p className="grain-note">{t(`grainNotes.${kpi.time_aggregation ?? "sum"}`)}</p> : null}
              {onIsolate ? (
                <div className="isolate-row">
                  <label className="check isolate">
                    <input
                      type="checkbox"
                      checked={isolate}
                      disabled={!canIsolate(kpi, grain)}
                      onChange={(e) => onIsolate(e.target.checked)}
                    />
                    {t("dashboard.isolate")}
                  </label>
                  {onAccumulate ? (
                    <label
                      className="check accumulate"
                      title={canAccumulate(kpi, isolate) ? t("dashboard.accumulateHint") : t(isolate ? "dashboard.accumulateSeasonalOff" : "dashboard.accumulateOff")}
                    >
                      <input
                        type="checkbox"
                        checked={accumulate}
                        disabled={!canAccumulate(kpi, isolate)}
                        onChange={(e) => onAccumulate(e.target.checked)}
                      />
                      {t("dashboard.accumulate")}
                    </label>
                  ) : null}
                </div>
              ) : null}
              {isolate && !canAccumulate(kpi, true) ? <p className="grain-note">{t("dashboard.accumulateSeasonalOff")}</p> : null}
            </fieldset>
          ) : null}
          {kpi.corrections?.length ? (
            <fieldset className="corrections">
              <legend>{t("dashboard.correction")}</legend>
              {[{ correction_id: null, label: t("dashboard.nominal"), note: "" }, ...kpi.corrections].map((c) => (
                <label key={c.correction_id ?? "nominal"} className="check">
                  <input
                    type="radio"
                    name="correcao"
                    checked={correction === c.correction_id}
                    onChange={() => onCorrection(c.correction_id)}
                  />
                  {c.label}
                </label>
              ))}
            </fieldset>
          ) : null}
          <fieldset className="period-filter">
            <legend>{t("dashboard.period")}</legend>
            <button
              type="button"
              className="period-summary"
              aria-expanded={periodsOpen}
              aria-controls="periodo-arvore"
              onClick={() => setPeriodsOpen((o) => !o)}
            >
              <span>{periodSummary}</span>
              <span className="period-summary-note">
                {t("dashboard.periodsChoose")} <span aria-hidden="true">{periodsOpen ? "▴" : "▾"}</span>
              </span>
            </button>
            {periodsOpen ? (
            <div id="periodo-arvore">
            {(() => {
              const { periods, complete } = grainPeriods(kpi, grain, level);
              const years = isolate;
              return (
                <PeriodFilter
                  key={`${grain ?? ""}|${isolate ? "y" : "p"}|${level}`}
                  leaves={years ? yearsOf(periods) : periods}
                  complete={years ? grainPeriods(kpi, "ano", level).complete : complete}
                  selected={selection}
                  onChange={onPeriods}
                />
              );
            })()}
            </div>
            ) : null}
            {selection.length > 1 && !accumulate && !isolate ? (
              <p className="grain-note">{t("dashboard.periodsNote", { count: selection.length })}</p>
            ) : null}
          </fieldset>
          {kpi.dimensions.length ? (
            <fieldset>
              <legend>{t("dashboard.dimensions")}</legend>
              {kpi.exclusive_dimensions ? (
                <p className="hint">
                  {kpi.crossed_levels?.length
                    ? kpi.crossed_levels.includes(level)
                      ? t("dashboard.dimensionsCrossed", {
                          groups: (kpi.crossed ?? [])
                            .map((g) =>
                              g.map((c) => kpi.dimensions.find((d) => d.classification_id === c)?.label ?? c).join(" × "),
                            )
                            .join("; "),
                        })
                      : t("dashboard.dimensionsCrossedElsewhere")
                    : t("dashboard.dimensionsExclusive")}
                </p>
              ) : null}
              {kpi.dimensions.map((d) => (
                <DimensionFilter
                  key={d.classification_id}
                  dimension={d}
                  level={level}
                  active={dimensions.includes(d.classification_id)}
                  chosen={categories.filter((k) => d.categories.some((c) => c.category_key === k))}
                  onChange={(on, keys) => {
                    // Dimensões marginais: ligar uma desliga as outras, salvo quando o
                    // grupo se cruza nesse nível (C1, até UF).
                    const id = d.classification_id;
                    const keep = !kpi.exclusive_dimensions || canCross(kpi, [...dimensions, id], level);
                    const next = new Set(keep || !on ? dimensions : []);
                    if (on) next.add(id);
                    else next.delete(id);
                    const dims = nav.dimension_order.filter((x) => next.has(x));
                    const others = categories.filter((k) => !d.categories.some((c) => c.category_key === k));
                    if (onDetail) onDetail(dims, on ? [...others, ...keys] : others);
                    else onDimensions(dims);
                  }}
                />
              ))}
              {categories.length ? (
                <p className="hint dim-filter-note">
                  {kpi.category_shares ? t("dashboard.filterSum") : t("dashboard.filterOfficial")}
                </p>
              ) : null}
            </fieldset>
          ) : null}
          </div>
          <div className="filters-foot">
            <button type="button" className="clear" onClick={onClear} disabled={!canClear}>
              {t("dashboard.clearFilters")}
            </button>
          </div>
        </section>
      ) : null}
      <nav className="themes" aria-label={t("dashboard.menu")}>
        <TreeSearch nav={nav} kpi={kpi} onKpi={onKpi} onPreload={onPreload} />
      </nav>
    </aside>
  );
}

function Marked({ text, query }: { text: string; query: string }) {
  return (
    <>
      {highlight(text, query).map((part, i) => (part.hit ? <mark key={i}>{part.text}</mark> : <span key={i}>{part.text}</span>))}
    </>
  );
}

function TreeSearch({ nav, kpi, onKpi, onPreload }: { nav: Navigation | PortalIndex; kpi: Kpi | null; onKpi: (id: string) => void; onPreload?: (id: string) => void }) {
  const t = useTranslations("dashboard");
  const [q, setQ] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const query = q.trim();

  // "/" em qualquer lugar (fora de campos) leva o foco à busca.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)) return;
      if (!input.current?.getClientRects().length) return; // no desktop, "/" abre o catálogo
      e.preventDefault();
      input.current.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const items = flatten<Kpi | KpiIndex>(nav);
  const hits = new Map(items.map((it) => [it.kpi.kpi_id, query ? matchKpi(it, query) : "label"]));
  // Em preparação (panorama): entram na árvore e na busca, sem ação (ainda sem dados).
  const pending = flattenPlanned(nav);
  const pendingHits = new Set(pending.filter((it) => !query || matchPlanned(it, query)).map((it) => it.planned.kpi_id));
  const count = [...hits.values()].filter(Boolean).length;
  const themeCount = new Set(items.filter((it) => hits.get(it.kpi.kpi_id)).map((it) => it.theme.theme_id)).size;
  const status = !query
    ? t("searchAll")
    : count
      ? t("searchCount", { count, themes: themeCount })
      : pendingHits.size
        ? t("searchPlannedOnly", { count: pendingHits.size })
        : t("searchNone");

  return (
    <>
      {/* Título, campo e resumo fixos no topo da área que rola (sticky): a busca fica à vista na árvore longa. */}
      <div className="tree-head">
        <h2>{t("menu")}</h2>
        <div role="search" className="tree-search">
          <label htmlFor="busca-indicador" className="sr-only">
            {t("searchLabel")}
          </label>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            ref={input}
            id="busca-indicador"
            type="search"
            value={q}
            placeholder={t("searchPlaceholder")}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setQ("");
            }}
          />
          {q ? null : <kbd aria-hidden="true">/</kbd>}
        </div>
        <div className="tree-status" aria-live="polite">
          <span>{status}</span>
          {query ? (
            <button type="button" onClick={() => setQ("")}>
              {t("searchClear")}
            </button>
          ) : null}
        </div>
      </div>
      {query && !count && !pendingHits.size ? (
        <div className="tree-empty">
          <strong>{t("searchEmptyTitle", { q: query })}</strong>
          <span>{t("searchEmptyHint")}</span>
        </div>
      ) : null}
      {nav.themes.map((theme) => {
        const subs = theme.subthemes
          .map((sub) => ({
            sub,
            kpis: sub.kpis.filter((k) => hits.get(k.kpi_id)),
            planned: sub.planned.filter((p) => pendingHits.has(p.kpi_id)),
          }))
          .filter((x) => x.kpis.length || x.planned.length);
        if (!subs.length) return null;
        // Sem busca, os temas ficam recolhidos e só o do indicador atual abre (20 temas).
        const current = theme.subthemes.some((s) => s.kpis.some((k) => k.kpi_id === kpi?.kpi_id));
        const live = theme.subthemes.some((s) => s.kpis.length > 0);
        return (
          <details key={`${theme.theme_id}-${query ? "q" : "n"}`} open={Boolean(query) || current}>
            <summary className={live ? undefined : "theme-planned"}>
              <span>
                <Marked text={theme.label} query={query} />
                {live ? null : <span className="planned-badge">{t("planned")}</span>}
              </span>
            </summary>
            {subs.map(({ sub, kpis, planned }) => (
              <details key={sub.subtheme_id} open={Boolean(query) || sub.kpis.some((k) => k.kpi_id === kpi?.kpi_id)}>
                <summary style={{ fontWeight: 700 }}>
                  <Marked text={sub.label} query={query} />
                </summary>
                <ul>
                  {kpis.map((k) => {
                    const where = hits.get(k.kpi_id);
                    const extra =
                      where === "description" ? k.description : where === "name" ? k.name : where === "table" ? t("searchTable", { id: sourceTable(k) }) : null;
                    return (
                      <li key={k.kpi_id}>
                        <button type="button" aria-pressed={k.kpi_id === kpi?.kpi_id} onClick={() => onKpi(k.kpi_id)} onMouseEnter={() => onPreload?.(k.kpi_id)} onFocus={() => onPreload?.(k.kpi_id)}>
                          <span className="tree-kpi">
                            <Marked text={k.label} query={query} />
                          </span>
                          {extra ? (
                            <span className="tree-snippet">
                              <Marked text={where === "table" ? extra : snippet(extra, query)} query={where === "table" ? "" : query} />
                            </span>
                          ) : null}
                        </button>
                      </li>
                    );
                  })}
                  {planned.map((p) => (
                    <li key={p.kpi_id} className="planned" title={t("plannedSource", { table: p.source_table_id, survey: p.survey })}>
                      <Marked text={p.label} query={query} />
                      <span className="planned-badge">{t("planned")}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </details>
        );
      })}
    </>
  );
}

interface DimensionFilterProps {
  dimension: Kpi["dimensions"][number];
  level: string;
  active: boolean;
  /** Categorias marcadas desta dimensão; vazio com a dimensão ativa: todas. */
  chosen: string[];
  /** on: dimensão ligada; keys: categorias marcadas (vazio: todas). */
  onChange: (on: boolean, keys: string[]) => void;
}

// "Detalhar por" como filtro hierárquico (DS 2.4): a dimensão marca todas as categorias;
// cada categoria pode ser marcada livremente. Mapa, tooltip, gráfico, tabela e
// exportação seguem a seleção (a API recalcula o Total quando o indicador é somável).
function DimensionFilter({ dimension: d, level, active, chosen, onChange }: DimensionFilterProps) {
  const t = useTranslations();
  // Recolhida por padrão (DS 2.9): "2 de 4" ao lado do nome; o botão abre e fecha.
  const [open, setOpen] = useState(false);
  const parent = useRef<HTMLInputElement>(null);
  const all = d.categories.map((c) => c.category_key);
  const marked = active ? (chosen.length ? chosen : all) : [];
  const partial = active && chosen.length > 0 && chosen.length < all.length;
  useEffect(() => {
    if (parent.current) parent.current.indeterminate = partial;
  }, [partial]);
  // A fonte só publica alguns detalhes em certos níveis (nota da tabela): fora deles,
  // a opção fica desabilitada e diz onde existe.
  const only = d.levels?.length && !d.levels.includes(level) ? d.levels : null;
  const where = only ? only.map((l) => t(`levels.${l}`)).join(", ") : "";
  const narrow = d.categories.every((c) => c.name.length <= 14);
  const toggle = (key: string, on: boolean) => {
    const next = on ? [...marked, key] : marked.filter((k) => k !== key);
    if (!next.length) onChange(false, []);
    else onChange(true, next.length === all.length ? [] : all.filter((k) => next.includes(k)));
  };
  const listId = `dim-cats-${d.classification_id}`;
  return (
    <div className={`dim-filter${only ? " is-unavailable" : ""}`}>
      <div className="dim-filter-head">
        <label
          className="check"
          title={
            only
              ? t("dashboard.dimensionOnlyAt", { levels: where })
              : d.full_label && d.full_label !== d.label
                ? d.full_label
                : undefined
          }
        >
          <input
            ref={parent}
            type="checkbox"
            disabled={Boolean(only) && !active}
            checked={active}
            aria-controls={listId}
            onChange={(e) => onChange(e.target.checked, [])}
          />
          {d.label}
          {only ? <span className="check-note">{t("dashboard.dimensionOnly", { levels: where })}</span> : null}
        </label>
        {!only && active ? (
          <span className="check-note dim-count">{t("dashboard.categoriesCount", { marked: marked.length, total: all.length })}</span>
        ) : null}
        {!only && d.categories.length ? (
          <button
            type="button"
            className="dim-filter-toggle"
            aria-expanded={open}
            aria-controls={listId}
            aria-label={open ? t("dashboard.hideCategories") : t("dashboard.showCategories", { count: d.categories.length })}
            onClick={() => setOpen(!open)}
          >
            <span aria-hidden="true">{open ? "▾" : "▸"}</span>
          </button>
        ) : null}
      </div>
      {!only && open ? (
        <div id={listId} className={`dim-cats${narrow ? " cols-2" : ""}`} role="group" aria-label={t("dashboard.categoriesOf", { dimension: d.label })}>
          {d.categories.map((c) => (
            <label key={c.category_key} className="check small" title={c.full_name && c.full_name !== c.name ? c.full_name : undefined}>
              <input
                type="checkbox"
                checked={marked.includes(c.category_key)}
                onChange={(e) => toggle(c.category_key, e.target.checked)}
              />
              {c.name}
            </label>
          ))}
        </div>
      ) : null}
    </div>
  );
}
