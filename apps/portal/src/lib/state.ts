// Estado do painel na URL (compartilhável): ?kpi=&nivel=&periodo=&dim=c86,c2&territorio=
import type { Kpi, Navigation } from "./types";

export interface DashboardState {
  kpi: string | null;
  level: string;
  period: string | null;
  dimensions: string[];
  geography: string;
}

export const DEFAULT_GEOGRAPHY = "brasil:1";

export function allKpis(nav: Navigation): Kpi[] {
  return nav.themes.flatMap((t) => t.subthemes.flatMap((s) => s.kpis));
}

export function readState(params: URLSearchParams, nav: Navigation): DashboardState {
  const kpis = allKpis(nav);
  const kpi = kpis.find((k) => k.kpi_id === params.get("kpi")) ?? kpis[0] ?? null;
  const levels = kpi?.map_levels.length ? kpi.map_levels : (kpi?.levels ?? []);
  const level = params.get("nivel");
  const exposed = new Set(kpi?.dimensions.map((d) => d.classification_id) ?? []);
  const dims = (params.get("dim") ?? "").split(",").filter((d) => exposed.has(d));
  const period = params.get("periodo");
  const geography = params.get("territorio");
  return {
    kpi: kpi?.kpi_id ?? null,
    level: level && kpi?.levels.includes(level) ? level : levels.includes("uf") ? "uf" : (levels[0] ?? "uf"),
    period: period && kpi?.periods.includes(period) ? period : null,
    dimensions: nav.dimension_order.filter((d) => dims.includes(d)),
    geography: geography && /^[a-z_]{2,32}:[0-9A-Za-z]{1,16}$/.test(geography) ? geography : DEFAULT_GEOGRAPHY,
  };
}

export function writeState(state: DashboardState): string {
  const params = new URLSearchParams();
  if (state.kpi) params.set("kpi", state.kpi);
  params.set("nivel", state.level);
  if (state.period) params.set("periodo", state.period);
  if (state.dimensions.length) params.set("dim", state.dimensions.join(","));
  if (state.geography !== DEFAULT_GEOGRAPHY) params.set("territorio", state.geography);
  return params.toString();
}
