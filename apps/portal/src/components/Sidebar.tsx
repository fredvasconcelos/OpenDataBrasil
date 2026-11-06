"use client";

import { useTranslations } from "next-intl";

import type { Kpi, Navigation } from "@/lib/types";

interface Props {
  nav: Navigation;
  kpi: Kpi | null;
  dimensions: string[];
  onKpi: (id: string) => void;
  onDimensions: (dims: string[]) => void;
}

// Menu lateral (cerca de 250 px): temas > subtemas > KPIs e as dimensões do KPI escolhido.
export function Sidebar({ nav, kpi, dimensions, onKpi, onDimensions }: Props) {
  const t = useTranslations("dashboard");
  return (
    <aside className="sidebar" aria-label={t("menu")}>
      <h2>{t("menu")}</h2>
      {nav.themes.map((theme) => (
        <details key={theme.theme_id} open>
          <summary>{theme.label}</summary>
          {theme.subthemes.map((sub) => (
            <details key={sub.subtheme_id} open={sub.kpis.some((k) => k.kpi_id === kpi?.kpi_id)}>
              <summary style={{ fontWeight: 500 }}>{sub.label}</summary>
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
      {kpi && kpi.dimensions.length ? (
        <fieldset>
          <legend>{t("dimensions")}</legend>
          {kpi.dimensions.map((d) => (
            <label key={d.classification_id} style={{ display: "block", padding: "2px 0" }}>
              <input
                type="checkbox"
                checked={dimensions.includes(d.classification_id)}
                onChange={(e) => {
                  const next = new Set(dimensions);
                  if (e.target.checked) next.add(d.classification_id);
                  else next.delete(d.classification_id);
                  onDimensions(nav.dimension_order.filter((x) => next.has(x)));
                }}
              />{" "}
              {d.label}
            </label>
          ))}
        </fieldset>
      ) : null}
    </aside>
  );
}
