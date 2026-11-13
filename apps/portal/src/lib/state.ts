// Estado do painel na URL (compartilhável): ?kpi=&nivel=&grao=&periodo=&dim=c86,c2&territorio=&foco=
import type { Kpi, Navigation } from "./types";
import { validFocus, zoomLadder } from "./zoom";

export interface DashboardState {
  kpi: string | null;
  level: string;
  /** Grão de tempo somado a partir do publicado (ADR-0013); null: o publicado. */
  grain: string | null;
  /** Correção por índice de preços (ADR-0020): id de `kpi.corrections`; null = nominal. */
  correction: string | null;
  period: string | null;
  dimensions: string[];
  geography: string;
  /** Recorte do mapa (ampliação seletiva): só ele se subdivide no nível exibido. */
  focus: string | null;
}

const GEOGRAPHY_KEY = /^[a-z_]{2,32}:[0-9A-Za-z]{1,16}$/;

export const DEFAULT_GEOGRAPHY = "brasil:1";

/**
 * Território inicial do KPI: o Brasil ou, sem ele, o recorte mais agregado
 * publicado (POF de 1987 e 1995: "Total das áreas", ADR-0016).
 */
export function defaultGeography(kpi: Kpi | null | undefined): string {
  if (!kpi || kpi.levels.includes("brasil") || !kpi.levels.includes("areas_pof")) return DEFAULT_GEOGRAPHY;
  return "areas_pof:1";
}

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
  const asked = params.get("correcao");
  const correction = asked && kpi?.corrections?.some((c) => c.correction_id === asked) ? asked : null;
  const geography = params.get("territorio");
  const focus = params.get("foco");
  const chosen = level && kpi?.levels.includes(level) ? level : defaultLevel(levels);
  return {
    kpi: kpi?.kpi_id ?? null,
    level: chosen,
    grain,
    correction,
    period: period && periods.includes(period) ? period : null,
    // Dimensões marginais (exclusive_dimensions): uma por vez.
    // Cruzamentos completos (C1): até UF, as dimensões de um mesmo grupo se cruzam.
    dimensions: (() => {
      // Detalhe que a fonte não publica neste nível (ex.: situação na PNS, só Brasil) sai.
      const atLevel = (d: string) => {
        const lv = kpi?.dimensions.find((x) => x.classification_id === d)?.levels ?? [];
        return !lv.length || lv.includes(chosen ?? "");
      };
      const asked = nav.dimension_order.filter((d) => dims.includes(d) && atLevel(d));
      return kpi?.exclusive_dimensions && !canCross(kpi, asked, chosen) ? asked.slice(0, 1) : asked;
    })(),
    // Território de um nível que o KPI não publica (ex.: o Brasil nas POF antigas) volta ao inicial.
    geography:
      geography && GEOGRAPHY_KEY.test(geography) && (!kpi || kpi.levels.includes(geography.split(":")[0] ?? ""))
        ? geography
        : defaultGeography(kpi),
    focus: focus && GEOGRAPHY_KEY.test(focus) && validFocus(zoomLadder(kpi?.map_levels ?? []), focus, chosen) ? focus : null,
  };
}

// O mapa abre no nível mais agregado da escada de zoom (Grande Região, quando houver).
// Sem mapa nem UF (POF de 1987 e 1995), a tabela abre nas regiões metropolitanas.
const PREFERRED_LEVELS = ["regiao", "uf", "regiao_metropolitana", "municipio"];

function defaultLevel(levels: string[]): string {
  return PREFERRED_LEVELS.find((l) => levels.includes(l)) ?? levels[0] ?? "regiao";
}

export function writeState(state: DashboardState): string {
  const params = new URLSearchParams();
  if (state.kpi) params.set("kpi", state.kpi);
  params.set("nivel", state.level);
  if (state.grain) params.set("grao", state.grain);
  if (state.correction) params.set("correcao", state.correction);
  if (state.period) params.set("periodo", state.period);
  if (state.dimensions.length) params.set("dim", state.dimensions.join(","));
  if (state.geography !== DEFAULT_GEOGRAPHY) params.set("territorio", state.geography);
  if (state.focus) params.set("foco", state.focus);
  return params.toString();
}

/** As dimensões se cruzam nesse nível? (C1: grupos em `crossed`, níveis em `crossed_levels`.) */
export function canCross(
  kpi: { crossed?: string[][]; crossed_levels?: string[] },
  dims: readonly string[],
  level: string | null,
): boolean {
  if (dims.length < 2) return true;
  if (!level || !(kpi.crossed_levels ?? []).includes(level)) return false;
  return (kpi.crossed ?? []).some((g) => dims.every((d) => g.includes(d)));
}
