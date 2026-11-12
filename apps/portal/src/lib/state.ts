// Estado do painel na URL (compartilhável): ?kpi=&nivel=&grao=&periodo=&dim=c86,c2&territorio=&foco=
import type { Kpi, Navigation } from "./types";
import { validFocus, zoomLadder } from "./zoom";

export interface DashboardState {
  kpi: string | null;
  level: string;
  /** Grão de tempo somado a partir do publicado (ADR-0013); null: o publicado. */
  grain: string | null;
  period: string | null;
  dimensions: string[];
  geography: string;
  /** Recorte do mapa (ampliação seletiva): só ele se subdivide no nível exibido. */
  focus: string | null;
}

const GEOGRAPHY_KEY = /^[a-z_]{2,32}:[0-9A-Za-z]{1,16}$/;

export const DEFAULT_GEOGRAPHY = "brasil:1";

export function allKpis(nav: Navigation): Kpi[] {
  return nav.themes.flatMap((t) => t.subthemes.flatMap((s) => s.kpis));
}

/** Grãos de tempo do KPI: o primeiro é o publicado; os demais, somas dos meses (fluxos). */
export function timeGrains(kpi: Kpi | null): Kpi["time_grains"] {
  return kpi?.time_grains ?? [];
}

/** Períodos do KPI no grão (todos e os completos). Sem grão, os publicados. */
export function grainPeriods(kpi: Kpi, grain: string | null): { periods: string[]; complete: string[] } {
  const found = grain ? timeGrains(kpi).find((g) => g.grain === grain) : undefined;
  return found
    ? { periods: found.periods, complete: found.complete_periods }
    : { periods: kpi.periods, complete: kpi.periods };
}

export function readState(params: URLSearchParams, nav: Navigation): DashboardState {
  const kpis = allKpis(nav);
  const kpi = kpis.find((k) => k.kpi_id === params.get("kpi")) ?? kpis[0] ?? null;
  const levels = kpi?.map_levels.length ? kpi.map_levels : (kpi?.levels ?? []);
  const level = params.get("nivel");
  const exposed = new Set(kpi?.dimensions.map((d) => d.classification_id) ?? []);
  const dims = (params.get("dim") ?? "").split(",").filter((d) => exposed.has(d));
  const period = params.get("periodo");
  const requested = params.get("grao");
  const grains = timeGrains(kpi);
  // O grão publicado (o primeiro) não vai na URL: null.
  const grain = requested && grains.slice(1).some((g) => g.grain === requested) ? requested : null;
  const periods = kpi ? grainPeriods(kpi, grain).periods : [];
  const geography = params.get("territorio");
  const focus = params.get("foco");
  const chosen = level && kpi?.levels.includes(level) ? level : defaultLevel(levels);
  return {
    kpi: kpi?.kpi_id ?? null,
    level: chosen,
    grain,
    period: period && periods.includes(period) ? period : null,
    dimensions: nav.dimension_order.filter((d) => dims.includes(d)),
    geography: geography && GEOGRAPHY_KEY.test(geography) ? geography : DEFAULT_GEOGRAPHY,
    focus: focus && GEOGRAPHY_KEY.test(focus) && validFocus(zoomLadder(kpi?.map_levels ?? []), focus, chosen) ? focus : null,
  };
}

// O mapa abre no nível mais agregado da escada de zoom (Grande Região, quando houver).
const PREFERRED_LEVELS = ["regiao", "uf", "municipio"];

function defaultLevel(levels: string[]): string {
  return PREFERRED_LEVELS.find((l) => levels.includes(l)) ?? levels[0] ?? "regiao";
}

export function writeState(state: DashboardState): string {
  const params = new URLSearchParams();
  if (state.kpi) params.set("kpi", state.kpi);
  params.set("nivel", state.level);
  if (state.grain) params.set("grao", state.grain);
  if (state.period) params.set("periodo", state.period);
  if (state.dimensions.length) params.set("dim", state.dimensions.join(","));
  if (state.geography !== DEFAULT_GEOGRAPHY) params.set("territorio", state.geography);
  if (state.focus) params.set("foco", state.focus);
  return params.toString();
}
