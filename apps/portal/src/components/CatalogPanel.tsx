"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { CloseIcon } from "@/components/icons";
import { ThemeIcon } from "@/components/ThemeIcon";
import { flatten, flattenPlanned, highlight, matchKpi, matchPlanned, snippet } from "@/lib/catalog";
import { themeStyle, themeVisual } from "@/lib/themes";
import type { Kpi, Navigation } from "@/lib/types";

interface Props {
  nav: Navigation;
  kpi: Kpi | null;
  onKpi: (id: string) => void;
  onClose: () => void;
  /** Posição na tela (ao lado da barra lateral), medida ao abrir. */
  place: { top: number; left: number; height: number };
}

function Marked({ text, query }: { text: string; query: string }) {
  return (
    <>
      {highlight(text, query).map((part, i) => (part.hit ? <mark key={i}>{part.text}</mark> : <span key={i}>{part.text}</span>))}
    </>
  );
}

// Painel "Escolher indicador" (DS 2.9, proposta B da barra lateral): abre ao lado da barra,
// por cima do mapa. Sem busca: temas à esquerda (com a contagem de indicadores) e, à
// direita, os subtemas e indicadores do tema escolhido (o do indicador atual, ao abrir).
// Com busca (sem acentos, também pelo nº da tabela): os achados de todos os temas, com o
// termo marcado. Esc ou clique fora fecham; o foco fica preso no painel e volta ao botão.
export function CatalogPanel({ nav, kpi, onKpi, onClose, place }: Props) {
  const t = useTranslations("dashboard");
  const [q, setQ] = useState("");
  const query = q.trim();
  const current = nav.themes.find((th) => th.subthemes.some((s) => s.kpis.some((k) => k.kpi_id === kpi?.kpi_id)));
  const [themeId, setThemeId] = useState(current?.theme_id ?? nav.themes[0]?.theme_id ?? "");
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    input.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !box.current) return;
      // Foco preso no painel (diálogo modal).
      const items = Array.from(
        box.current.querySelectorAll<HTMLElement>("button:not(:disabled), input, [href], [tabindex]:not([tabindex='-1'])"),
      );
      const first = items[0];
      const last = items.at(-1);
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const items = flatten(nav);
  const planned = flattenPlanned(nav);
  const hits = query ? items.filter((it) => matchKpi(it, query)) : [];
  const plannedHits = query ? planned.filter((it) => matchPlanned(it, query)) : [];
  const count = (id: string) =>
    query
      ? hits.filter((it) => it.theme.theme_id === id).length
      : (nav.themes.find((th) => th.theme_id === id)?.subthemes.reduce((n, s) => n + s.kpis.length, 0) ?? 0);
  const theme = nav.themes.find((th) => th.theme_id === themeId) ?? nav.themes[0];
  const pick = (id: string) => {
    onKpi(id);
    onClose();
  };
  const kpiButton = (k: Kpi, extra: string | null) => (
    <li key={k.kpi_id}>
      <button type="button" aria-pressed={k.kpi_id === kpi?.kpi_id} onClick={() => pick(k.kpi_id)}>
        <span className="tree-kpi">
          <Marked text={k.label} query={query} />
          {k.kpi_id === kpi?.kpi_id ? <span className="catalog-current"> · {t("catalogCurrent")}</span> : null}
        </span>
        {extra ? (
          <span className="tree-snippet">
            <Marked text={extra} query={query} />
          </span>
        ) : null}
      </button>
    </li>
  );

  return (
    <>
      <button type="button" className="catalog-backdrop" aria-label={t("catalogClose")} tabIndex={-1} onClick={onClose} />
      <div
        ref={box}
        className="catalog-panel"
        role="dialog"
        aria-modal="true"
        aria-label={t("catalogTitle")}
        style={{ top: place.top, left: place.left, height: place.height }}
      >
        <div className="catalog-head">
          <div role="search" className="tree-search">
            <label htmlFor="catalogo-busca" className="sr-only">
              {t("searchLabel")}
            </label>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              ref={input}
              id="catalogo-busca"
              type="search"
              value={q}
              placeholder={t("catalogSearch")}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <button type="button" className="icon-btn" aria-label={t("catalogClose")} title={t("catalogClose")} onClick={onClose}>
            <CloseIcon size={18} />
          </button>
        </div>
        <div className="catalog-body">
          <nav className="catalog-themes" aria-label={t("catalogThemes")}>
            <ul>
              {nav.themes.map((th) => {
                const n = count(th.theme_id);
                if (query && !n) return null;
                const visual = themeVisual(th);
                const live = th.subthemes.some((s) => s.kpis.length > 0);
                return (
                  <li key={th.theme_id} style={themeStyle(visual.family)}>
                    <button
                      type="button"
                      aria-pressed={!query && th.theme_id === theme?.theme_id}
                      className={live ? undefined : "theme-planned"}
                      onClick={() => {
                        setThemeId(th.theme_id);
                        setQ("");
                      }}
                    >
                      <ThemeIcon icon={visual.icon} size={15} box={26} />
                      <span className="catalog-theme-label">{th.label}</span>
                      <span className="catalog-count">{n}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          <div className="catalog-list" aria-live="polite">
            {query ? (
              <>
                <p className="catalog-status">
                  {hits.length
                    ? t("searchCount", { count: hits.length, themes: new Set(hits.map((h) => h.theme.theme_id)).size })
                    : plannedHits.length
                      ? t("searchPlannedOnly", { count: plannedHits.length })
                      : t("searchEmptyTitle", { q: query })}
                </p>
                {nav.themes.map((th) => {
                  const mine = hits.filter((h) => h.theme.theme_id === th.theme_id);
                  if (!mine.length) return null;
                  return (
                    <section key={th.theme_id}>
                      <h3>
                        <Marked text={th.label} query={query} />
                      </h3>
                      <ul>
                        {mine.map((h) => {
                          const where = matchKpi(h, query);
                          const extra =
                            where === "description"
                              ? snippet(h.kpi.description, query)
                              : where === "name"
                                ? snippet(h.kpi.name, query)
                                : where === "table"
                                  ? t("searchTable", { id: h.kpi.source.source_table_id })
                                  : h.subthemeLabel;
                          return kpiButton(h.kpi, extra);
                        })}
                      </ul>
                    </section>
                  );
                })}
                {plannedHits.length ? (
                  <ul>
                    {plannedHits.map((p) => (
                      <li key={p.planned.kpi_id} className="planned" title={t("plannedSource", { table: p.planned.source_table_id, survey: p.planned.survey })}>
                        <Marked text={p.planned.label} query={query} />
                        <span className="planned-badge">{t("planned")}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {!hits.length && !plannedHits.length ? <p className="catalog-status">{t("searchEmptyHint")}</p> : null}
              </>
            ) : theme ? (
              <>
                <h3 className="catalog-title">{theme.label}</h3>
                {theme.subthemes
                  .filter((s) => s.kpis.length || s.planned.length)
                  .map((s) => (
                    <section key={s.subtheme_id}>
                      <h4>{s.label}</h4>
                      <ul>
                        {s.kpis.map((k) => kpiButton(k, null))}
                        {s.planned.map((p) => (
                          <li key={p.kpi_id} className="planned" title={t("plannedSource", { table: p.source_table_id, survey: p.survey })}>
                            {p.label}
                            <span className="planned-badge">{t("planned")}</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
              </>
            ) : null}
          </div>
        </div>
        <p className="catalog-hint">{t("catalogHint")}</p>
      </div>
    </>
  );
}
