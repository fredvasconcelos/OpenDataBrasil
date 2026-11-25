// Estado do painel na URL (compartilhável): ?kpi=&nivel=&grao=&periodo=2025T1,2025T2&acumular=1&dim=c86,c2&cat=c86:2776&territorio=&foco=
import type { Kpi, KpiIndex, Navigation, PortalIndex } from "./types";
import { parsePeriod } from "./period";
import { validFocus, zoomLadder } from "./zoom";

export interface DashboardState {
  kpi: string | null;
  level: string;
  /** Grão de tempo somado a partir do publicado (ADR-0013); null: o publicado. */
  grain: string | null;
  /** Correção por índice de preços (ADR-0020): id de `kpi.corrections`; null = nominal. */
  correction: string | null;
  /** Período do mapa: o último da seleção (null: o padrão, último completo). */
  period: string | null;
  /** Seleção de períodos (ADR-0026): folhas no grão de "Período por" ou, com Isolar,
   * anos. Com mais de um, a tabela ganha uma coluna por período. */
  periods: string[];
  /** "Acumular" (ADR-0026): soma (fluxos) ou composição (variações %) da seleção. */
  accumulate: boolean;
  dimensions: string[];
  /** Filtro do Detalhar por (DS 2.4): categorias marcadas das dimensões ativas; sem
   * chave de uma dimensão, todas. Em indicadores somáveis, o Total vira a soma delas. */
  categories: string[];
  geography: string;
  /** Recorte do mapa (ampliação seletiva): só ele se subdivide no nível exibido. */
  focus: string | null;
  /** "Isolar período" (DS 2.3.14): a parte do ano acumulada entre os anos (barras). */
  isolate: boolean;
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

export function allKpis<T>(nav: { themes: { subthemes: { kpis: T[] }[] }[] }): T[] {
  return nav.themes.flatMap((t) => t.subthemes.flatMap((s) => s.kpis));
}

/** A escolha inicial segue a ordem publicada, inclusive com um id inválido na URL. */
export function resolveKpiId(params: URLSearchParams, index: PortalIndex | Navigation): string | null {
  const ids = index.themes.flatMap((t) => t.subthemes.flatMap((s) => s.kpis.map((k) => k.kpi_id)));
  const requested = params.get("kpi");
  return requested && ids.includes(requested) ? requested : ids[0] ?? null;
}

/** Grãos de tempo do KPI: o primeiro é o publicado; os demais, somas dos meses (fluxos). */
export function timeGrains(kpi: Kpi | null): Kpi["time_grains"] {
  return kpi?.time_grains ?? [];
}

/** Períodos do KPI no grão (todos e os completos). Sem grão, os publicados. */
export function grainPeriods(kpi: Kpi, grain: string | null, level?: string): { periods: string[]; complete: string[] } {
  const found = grain ? timeGrains(kpi).find((g) => g.grain === grain) : undefined;
  const covered = level ? kpi.periods_by_level?.[level] : undefined;
  if (!found) {
    const periods = covered ?? kpi.periods;
    return { periods, complete: periods };
  }
  if (!covered) return { periods: found.periods, complete: found.complete_periods };
  // A cobertura é do grão publicado. Um ano municipal com seis meses não pode
  // herdar o estado "completo" dos doze meses publicados para o Brasil.
  const nativeParts = { year: 1, semester: 2, quarter: 4, month: 12 };
  const targetParts = { ano: 1, semestre: 2, trimestre: 4, mes: 12 }[found.grain];
  if (!targetParts) return { periods: found.periods, complete: found.complete_periods };
  const counts = new Map<string, number>();
  let needed = 1;
  for (const raw of covered) {
    const parsed = parsePeriod(raw);
    if (!parsed) continue;
    const parts = nativeParts[parsed.granularity];
    const year = Math.floor(parsed.unit / parts);
    const index = Math.floor((parsed.unit % parts) * targetParts / parts) + 1;
    const code = found.grain === "ano" ? String(year)
      : `${year}${found.grain === "semestre" ? "S" : found.grain === "trimestre" ? "T" : "M"}${found.grain === "mes" ? String(index).padStart(2, "0") : index}`;
    counts.set(code, (counts.get(code) ?? 0) + 1);
    needed = parts / targetParts;
  }
  return {
    periods: found.periods.filter((p) => counts.has(p)),
    complete: found.complete_periods.filter((p) => (counts.get(p) ?? 0) >= needed),
  };
}

/** O KPI admite acumular períodos? Só fluxos (soma) e variações % (composição). */
export function canAccumulate(kpi: Kpi | null, isolate = false): boolean {
  if (kpi?.temporal) return isolate ? kpi.temporal.seasonal_sum : kpi.temporal.accumulate;
  return timeGrains(kpi).length > 1 && (isolate
    ? kpi?.time_aggregation === "sum" : ["sum", "compound"].includes(kpi?.time_aggregation ?? ""));
}

/** Comparar partes é independente de somar períodos (ADR-0041). */
export function canIsolate(kpi: Kpi | null, grain: string | null): boolean {
  return kpi?.temporal?.isolate ?? (timeGrains(kpi).length > 1
    && (grain ?? timeGrains(kpi)[0]?.grain ?? "ano") !== "ano");
}

/** Anos (em ordem) que contêm os períodos dados. */
export function yearsOf(periods: readonly string[]): string[] {
  return [...new Set(periods.map((p) => p.slice(0, 4)))].sort();
}

/** Períodos selecionáveis: no grão escolhido ou, com Isolar, os anos. */
export function selectablePeriods(kpi: Kpi, grain: string | null, level: string, isolate: boolean): string[] {
  const { periods } = grainPeriods(kpi, grain, level);
  return isolate ? yearsOf(periods) : periods;
}

/** Categorias válidas: só das dimensões ativas, e nenhuma dimensão com todas marcadas. */
export function normalizeCategories(kpi: Kpi | null, dims: readonly string[], keys: readonly string[]): string[] {
  const out: string[] = [];
  for (const d of kpi?.dimensions ?? []) {
    if (!dims.includes(d.classification_id)) continue;
    const all = d.categories.map((c) => c.category_key);
    const chosen = all.filter((k) => keys.includes(k));
    if (chosen.length && chosen.length < all.length) out.push(...chosen);
  }
  return out;
}

export function readState(params: URLSearchParams, nav: Navigation | PortalIndex, current?: Kpi | null): DashboardState {
  const id = resolveKpiId(params, nav);
  const entry = allKpis<Kpi | KpiIndex>(nav).find((k) => k.kpi_id === id);
  const kpi = current?.kpi_id === id ? current : entry && "levels" in entry ? entry : null;
  const state = readBase(params, nav, kpi, id);
  const keys = (params.get("cat") ?? "").split(",").filter(Boolean);
  return { ...state, categories: normalizeCategories(kpi, state.dimensions, keys) };
}

function readBase(params: URLSearchParams, nav: Navigation | PortalIndex, kpi: Kpi | null, id: string | null): DashboardState {
  const levels = kpi?.map_levels.length ? kpi.map_levels : (kpi?.levels ?? []);
  const level = params.get("nivel");
  const chosen = level && kpi?.levels.includes(level) ? level : defaultLevel(levels);
  const exposed = new Set(kpi?.dimensions.map((d) => d.classification_id) ?? []);
  const dims = (params.get("dim") ?? "").split(",").filter((d) => exposed.has(d));
  const asked_periods = (params.get("periodo") ?? "").split(",").filter(Boolean);
  const requested = params.get("grao");
  const grains = timeGrains(kpi);
  // O grão publicado (o primeiro) não vai na URL: null.
  const grain = requested && grains.slice(1).some((g) => g.grain === requested) ? requested : null;
  // Só com grão menor que o ano (mês, trimestre ou semestre).
  const isolate = params.get("isolar") === "1" && canIsolate(kpi, grain);
  const valid = kpi ? selectablePeriods(kpi, grain, chosen, isolate) : [];
  const picked = valid.filter((p) => asked_periods.includes(p));
  const asked = params.get("correcao");
  const correction = asked && kpi?.corrections?.some((c) => c.correction_id === asked) ? asked : null;
  const geography = params.get("territorio");
  const focus = params.get("foco");
  return {
    kpi: id,
    level: chosen,
    grain,
    isolate,
    correction,
    period: picked.at(-1) ?? null,
    periods: picked,
    accumulate: params.get("acumular") === "1" && canAccumulate(kpi, isolate),
    // Dimensões marginais (exclusive_dimensions): uma por vez.
    // Cruzamentos completos (C1): até UF, as dimensões de um mesmo grupo se cruzam.
    dimensions: (() => {
      // Detalhe que a fonte não publica neste nível (ex.: situação na PNS, só Brasil) fica
      // pedido (DS 2.9): a tabela mostra o Total e o botão i avisa; volta ao trocar o nível.
      const asked = nav.dimension_order.filter((d) => dims.includes(d));
      return kpi?.exclusive_dimensions && !canCross(kpi, asked, chosen) ? asked.slice(0, 1) : asked;
    })(),
    categories: [],
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
  if (state.periods.length > 1) params.set("periodo", state.periods.join(","));
  else if (state.period) params.set("periodo", state.period);
  if (state.accumulate) params.set("acumular", "1");
  if (state.dimensions.length) params.set("dim", state.dimensions.join(","));
  if (state.categories.length) params.set("cat", state.categories.join(","));
  if (state.geography !== DEFAULT_GEOGRAPHY) params.set("territorio", state.geography);
  if (state.focus) params.set("foco", state.focus);
  if (state.isolate) params.set("isolar", "1");
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

/** Parâmetros de período das consultas do painel (ADR-0026). */
export interface PeriodQuery {
  map: { period: string | null; grain: string | null; periods: string[]; accumulate: boolean };
  table: {
    period: string | null;
    grain: string | null;
    periods: string[];
    accumulate: "total" | "running" | "year" | null;
  };
  series: { periods: string[]; accumulate: "running" | "year" | null };
  /** Seleção efetiva (folhas ou anos), em ordem; vazia: o padrão da API. */
  selection: string[];
}

/**
 * Da seleção do usuário às consultas:
 * - Isolar: o mapa mostra o ano (o último marcado); tabela e gráfico, as partes dos anos
 *   marcados; com Acumular, o acumulado no ano (jan, jan+fev, …).
 * - Vários períodos: a tabela ganha uma coluna por período e o mapa mostra o último;
 *   com Acumular, mapa e tabela mostram a soma (ou composição) e o gráfico, a curva acumulada.
 */
export function periodQuery(kpi: Kpi | null, state: DashboardState): PeriodQuery {
  const selection = state.periods.length ? state.periods : state.period ? [state.period] : [];
  const none: PeriodQuery = {
    map: { period: state.period, grain: state.grain, periods: [], accumulate: false },
    table: { period: state.period, grain: state.grain, periods: [], accumulate: null },
    series: { periods: [], accumulate: null },
    selection,
  };
  if (!kpi) return none;
  if (state.isolate) {
    const { periods, complete } = grainPeriods(kpi, state.grain, state.level);
    const fallback = complete.at(-1) ?? periods.at(-1);
    let years = selection.length ? selection : fallback ? yearsOf([fallback]) : [];
    if (state.accumulate && years.length) {
      const from = Number(years[0]), to = Number(years.at(-1));
      years = Array.from({ length: to - from + 1 }, (_, i) => String(from + i));
    }
    const parts = periods.filter((p) => years.includes(p.slice(0, 4)));
    const hasYear = timeGrains(kpi).some((g) => g.grain === "ano");
    return {
      map: { period: hasYear ? years.at(-1) ?? null : parts.at(-1) ?? null,
        grain: hasYear ? "ano" : state.grain, periods: [], accumulate: false },
      table: { period: null, grain: state.grain, periods: parts, accumulate: null },
      // O modo combinado usa /seasonal; nunca pedir o antigo acumulado no ano.
      series: { periods: years, accumulate: null },
      selection: years,
    };
  }
  if (state.accumulate) {
    return {
      map: { period: null, grain: state.grain, periods: selection, accumulate: true },
      table: { period: null, grain: state.grain, periods: selection, accumulate: "total" },
      series: { periods: selection, accumulate: "running" },
      selection,
    };
  }
  if (selection.length > 1) {
    return {
      ...none,
      map: { period: selection.at(-1) ?? null, grain: state.grain, periods: [], accumulate: false },
      table: { period: null, grain: state.grain, periods: selection, accumulate: null },
    };
  }
  return none;
}
