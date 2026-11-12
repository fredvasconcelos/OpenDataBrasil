"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { flatten, flattenPlanned, highlight, matchKpi, matchPlanned, snippet } from "@/lib/catalog";
import type { Kpi, Navigation } from "@/lib/types";
import { formatPeriod } from "@/lib/format";

interface Props {
  nav: Navigation;
  kpi: Kpi | null;
  dimensions: string[];
  onKpi: (id: string) => void;
  onDimensions: (dims: string[]) => void;
  /** Filtros do indicador atual (nível territorial e período). */
  level: string;
  period: string;
  onLevel: (level: string) => void;
  onPeriod: (period: string) => void;
  /** Volta os filtros ao estado inicial do indicador (desativado se já estiverem nele). */
  onClear: () => void;
  canClear: boolean;
}

// Barra lateral (Design System ODBr): no topo, o bloco "Filtros" (nível territorial,
// período e "Detalhar por"); abaixo, "Temas e indicadores" (temas > subtemas > KPIs).
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
  onDimensions,
  level,
  period,
  onLevel,
  onPeriod,
  onClear,
  canClear,
}: Props) {
  const t = useTranslations();
  return (
    <aside className="sidebar">
      {kpi ? (
        <section className="filters" aria-label={t("dashboard.filters")}>
          <h2>{t("dashboard.filters")}</h2>
          <label className="field">
            {t("dashboard.level")}
            <select value={level} onChange={(e) => onLevel(e.target.value)}>
              {kpi.levels.map((l) => (
                <option key={l} value={l}>
                  {t(`levels.${l}`)}
                  {kpi.map_levels.includes(l) ? "" : " (sem mapa)"}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            {t("dashboard.period")}
            <select value={period} onChange={(e) => onPeriod(e.target.value)}>
              {kpi.periods.map((p) => (
                <option key={p} value={p}>
                  {formatPeriod(p)}
                </option>
              ))}
            </select>
          </label>
          {kpi.dimensions.length ? (
            <fieldset>
              <legend>{t("dashboard.dimensions")}</legend>
              {kpi.dimensions.map((d) => (
                <label key={d.classification_id} className="check">
                  <input
                    type="checkbox"
                    checked={dimensions.includes(d.classification_id)}
                    onChange={(e) => {
                      const next = new Set(dimensions);
                      if (e.target.checked) next.add(d.classification_id);
                      else next.delete(d.classification_id);
                      onDimensions(nav.dimension_order.filter((x) => next.has(x)));
                    }}
                  />
                  {d.label}
                </label>
              ))}
            </fieldset>
          ) : null}
          <button type="button" className="clear" onClick={onClear} disabled={!canClear}>
            {t("dashboard.clearFilters")}
          </button>
        </section>
      ) : null}
      <nav className="themes" aria-label={t("dashboard.menu")}>
        <TreeSearch nav={nav} kpi={kpi} onKpi={onKpi} />
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

function TreeSearch({ nav, kpi, onKpi }: { nav: Navigation; kpi: Kpi | null; onKpi: (id: string) => void }) {
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
      e.preventDefault();
      input.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const items = flatten(nav);
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
                      where === "description" ? k.description : where === "name" ? k.name : where === "table" ? t("searchTable", { id: k.source.source_table_id }) : null;
                    return (
                      <li key={k.kpi_id}>
                        <button type="button" aria-pressed={k.kpi_id === kpi?.kpi_id} onClick={() => onKpi(k.kpi_id)}>
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
