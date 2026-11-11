"use client";

import { useTranslations } from "next-intl";
import { type CSSProperties, useMemo, useState } from "react";

import { KpiPreview } from "@/components/KpiPreview";
import { ThemeIcon } from "@/components/ThemeIcon";
import { type CatalogKpi, flatten, flattenPlanned, matchKpi, matchPlanned } from "@/lib/catalog";
import { THEME_ICONS, themeStyle, themeVisual } from "@/lib/themes";
import type { Navigation, Theme } from "@/lib/types";

const SAMPLE = 4;

// Início (Design System ODBr v2.3): busca, etiquetas de tema (filtro), grade compacta de
// temas em "Todos" e lista completa ao escolher um tema ou buscar. Clicar num indicador
// abre a prévia (KpiPreview). A busca também acha o número da tabela da fonte.
// Os indicadores em preparação (panorama) aparecem nas listas, sem ação, com a etiqueta.
export function HomeCatalog({ nav, releaseId }: { nav: Navigation; releaseId: string | null }) {
  const t = useTranslations();
  const [q, setQ] = useState("");
  const [theme, setTheme] = useState<string>("all");
  const [open, setOpen] = useState<CatalogKpi | null>(null);
  const items = useMemo(() => flatten(nav), [nav]);
  const query = q.trim();
  const pending = useMemo(() => flattenPlanned(nav), [nav]);
  const inTheme = (id: string) => theme === "all" || id === theme;
  const found = items.filter((it) => inTheme(it.theme.theme_id) && (!query || matchKpi(it, query)));
  const foundPending = pending.filter((it) => inTheme(it.theme.theme_id) && (!query || matchPlanned(it, query)));
  const grid = theme === "all" && !query;
  const byTheme = (th: Theme) => found.filter((it) => it.theme.theme_id === th.theme_id);
  const countOf = (th: Theme) => th.subthemes.reduce((n, s) => n + s.kpis.length, 0);
  const pendingOf = (th: Theme) => foundPending.filter((it) => it.theme.theme_id === th.theme_id);
  const summary = (published: number, planned: number) =>
    !planned
      ? t("catalog.kpiCount", { count: published })
      : published
        ? `${t("catalog.kpiCount", { count: published })} · ${t("catalog.plannedCount", { count: planned })}`
        : t("catalog.plannedCount", { count: planned });
  const shown = nav.themes.filter((th) => byTheme(th).length > 0 || pendingOf(th).length > 0);
  const tables = new Set(items.map((it) => it.kpi.source.source_table_id));

  return (
    <>
      <section className="home-hero">
        <h1>{t("home.title")}</h1>
        <p className="lead">{t("home.lead")}</p>
        <ul className="home-stats">
          <li>
            <strong>{items.length.toLocaleString("pt-BR")}</strong> {t("catalog.statKpis")}
          </li>
          <li>
            <strong>{pending.length.toLocaleString("pt-BR")}</strong> {t("catalog.statPlanned")}
          </li>
          <li>
            <strong>{nav.themes.length}</strong> {t("catalog.statThemes")}
          </li>
          <li>
            <strong>{tables.size}</strong> {t("catalog.statTables")}
          </li>
        </ul>
        <div role="search" className="home-search">
          <label htmlFor="home-busca">{t("home.searchLabel")}</label>
          <SearchGlyph />
          <input id="home-busca" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("home.searchPlaceholder")} />
          <p aria-live="polite" className="home-search-status">
            {query
              ? foundPending.length
                ? `${t("catalog.found", { count: found.length })} · ${t("catalog.plannedCount", { count: foundPending.length })}`
                : t("catalog.found", { count: found.length })
              : t("catalog.searchHint")}
          </p>
        </div>
      </section>

      <section className="theme-chips" aria-label={t("catalog.filterByTheme")}>
        <h2 className="eyebrow">{t("home.themes")}</h2>
        <div>
          <Chip on={theme === "all"} label={t("catalog.all")} count={items.length} onClick={() => setTheme("all")} />
          {nav.themes.map((th) => {
            const v = themeVisual(th);
            return (
              <Chip
                key={th.theme_id}
                on={theme === th.theme_id}
                label={th.label}
                count={countOf(th)}
                icon={THEME_ICONS[v.icon]}
                style={themeStyle(v.family)}
                onClick={() => setTheme(th.theme_id)}
              />
            );
          })}
        </div>
      </section>

      {grid ? (
        <div className="theme-grid">
          {nav.themes.map((th) => {
            const v = themeVisual(th);
            const list = byTheme(th);
            return (
              <section key={th.theme_id} className="theme-card" aria-labelledby={`tema-${th.theme_id}`} style={themeStyle(v.family)}>
                <div className="theme-card-head">
                  <ThemeIcon icon={v.icon} />
                  <div>
                    <h2 id={`tema-${th.theme_id}`}>{th.label}</h2>
                    <span>{summary(countOf(th), pendingOf(th).length)}</span>
                  </div>
                </div>
                <ul>
                  {list.slice(0, SAMPLE).map((it) => (
                    <li key={it.kpi.kpi_id}>
                      <button type="button" className="kpi-link" aria-haspopup="dialog" onClick={() => setOpen(it)}>
                        {it.kpi.label}
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="theme-card-foot">
                  <button type="button" className="text-btn" onClick={() => setTheme(th.theme_id)}>
                    {list.length > SAMPLE ? t("catalog.seeAll", { count: list.length }) : t("catalog.seeTheme")}
                  </button>
                </div>
              </section>
            );
          })}
        </div>
      ) : shown.length ? (
        shown.map((th) => {
          const v = themeVisual(th);
          const list = byTheme(th);
          return (
            <section key={th.theme_id} className="theme-panel" aria-labelledby={`lista-${th.theme_id}`} style={themeStyle(v.family)}>
              <div className="theme-panel-head">
                <ThemeIcon icon={v.icon} size={24} box={46} />
                <div>
                  <h2 id={`lista-${th.theme_id}`}>{th.label}</h2>
                  <span>{summary(list.length, pendingOf(th).length)}</span>
                </div>
              </div>
              <div className="theme-panel-cols">
                {th.subthemes.map((s) => {
                  const kpis = list.filter((it) => it.subthemeLabel === s.label);
                  const planned = pendingOf(th).filter((it) => it.subthemeLabel === s.label);
                  if (!kpis.length && !planned.length) return null;
                  return (
                    <div key={s.subtheme_id}>
                      {s.label ? <h3>{s.label}</h3> : null}
                      <ul>
                        {kpis.map((it) => (
                          <li key={it.kpi.kpi_id}>
                            <button type="button" className="kpi-link" aria-haspopup="dialog" onClick={() => setOpen(it)}>
                              {it.kpi.label}
                            </button>
                          </li>
                        ))}
                        {planned.map((it) => (
                          <li key={it.planned.kpi_id}>
                            <span
                              className="kpi-pending"
                              title={t("dashboard.plannedSource", { table: it.planned.source_table_id, survey: it.planned.survey })}
                            >
                              {it.planned.label}
                              <span className="planned-badge">{t("dashboard.planned")}</span>
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })
      ) : (
        <p className="empty">{t("catalog.empty")}</p>
      )}

      {open ? <KpiPreview item={open} releaseId={releaseId} onClose={() => setOpen(null)} /> : null}
    </>
  );
}

function Chip({
  on,
  label,
  count,
  icon = THEME_ICONS.generico,
  style,
  onClick,
}: {
  on: boolean;
  label: string;
  count: number;
  icon?: string;
  style?: CSSProperties;
  onClick: () => void;
}) {
  return (
    <button type="button" className="theme-chip" aria-pressed={on} onClick={onClick} style={style}>
      <span className="theme-chip-icon" aria-hidden="true">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d={icon} />
        </svg>
      </span>
      {label}
      <span className="theme-chip-count">{count}</span>
    </button>
  );
}

export function SearchGlyph() {
  return (
    <svg className="search-glyph" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </svg>
  );
}
