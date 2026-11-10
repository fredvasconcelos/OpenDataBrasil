"use client";

import { useTranslations } from "next-intl";

import type { Kpi, Navigation } from "@/lib/types";

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
}

// Barra lateral (Design System ODBr): no topo, o bloco "Filtros" (nível territorial,
// período e "Detalhar por"); abaixo, "Temas e indicadores" (temas > subtemas > KPIs).
// Todos os filtros do portal ficam aqui; a área central só tem conteúdo e exportações.
export function Sidebar({ nav, kpi, dimensions, onKpi, onDimensions, level, period, onLevel, onPeriod }: Props) {
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
                  {p}
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
        </section>
      ) : null}
      <nav className="themes" aria-label={t("dashboard.menu")}>
        <h2>{t("dashboard.menu")}</h2>
        {nav.themes.map((theme) => (
          <details key={theme.theme_id} open>
            <summary>{theme.label}</summary>
            {theme.subthemes.map((sub) => (
              <details key={sub.subtheme_id} open={sub.kpis.some((k) => k.kpi_id === kpi?.kpi_id)}>
                <summary style={{ fontWeight: 700 }}>{sub.label}</summary>
                <ul>
                  {sub.kpis.map((k) => (
                    <li key={k.kpi_id}>
                      <button type="button" aria-pressed={k.kpi_id === kpi?.kpi_id} onClick={() => onKpi(k.kpi_id)}>
                        {k.label}
                      </button>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </details>
        ))}
      </nav>
    </aside>
  );
}
