// Cliente da API. No navegador, as chamadas passam pelo proxy do próprio portal
// (/odb-api → API interna); no servidor, vão direto à URL interna.
import type {
  Dataset,
  History,
  Pivot,
  Source,
  Detail,
  ExportFormat,
  ExportOptions,
  GeoCollection,
  Geography,
  Indicator,
  Kpi,
  MapData,
  Navigation,
  PortalIndex,
  Release,
  Series,
  Table,
} from "./types";
import { periodParams } from "./metrics";
import type { DatasetSort, DatasetsResponse, GeoLevel, GeoResponse, MetricsSummary, PeriodRequest } from "./metrics";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

function base(): string {
  if (typeof window === "undefined") {
    const internal = process.env.ODB_API_INTERNAL_URL ?? "http://localhost:8000";
    return `${internal.replace(/\/$/, "")}/api/v1`;
  }
  return "/odb-api";
}

type Params = Record<string, string | number | boolean | readonly string[] | null | undefined>;

export function query(params: Params): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "" || value === false) continue;
    if (Array.isArray(value)) {
      if (value.length) search.set(key, value.join(","));
    } else {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let code = "http_error";
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { error?: { code: string; message: string } };
      if (body.error) ({ code, message } = body.error);
    } catch {
      // corpo não é JSON
    }
    throw new ApiRequestError(response.status, code, message);
  }
  return (await response.json()) as T;
}

/** 404 (endpoint ou dado ainda inexistente) vira null; os demais erros seguem. */
async function orNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (e) {
    if (e instanceof ApiRequestError && e.status === 404) return null;
    throw e;
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  return parse<T>(await fetch(`${base()}${path}`, { ...init, headers: { Accept: "application/json" } }));
}

const noStore: RequestInit = { cache: "no-store" };

export const api = {
  index: () => get<PortalIndex>("/portal/index", noStore),
  navigation: () => get<Navigation>("/portal/navigation", noStore),
  release: () => get<Release>("/release", noStore),
  datasets: () => get<Dataset[]>("/datasets", noStore),
  sources: () => get<Source[]>("/sources", noStore),
  indicators: (q?: string) => get<Indicator[]>(`/indicators${query({ q })}`, noStore),
  kpi: async (id: string, release?: string) => {
    const snapshot = await api.kpiSnapshot(id);
    if (release && snapshot.releaseId !== release) {
      throw new ApiRequestError(409, "release_changed", "release_changed");
    }
    return snapshot.kpi;
  },
  kpiSnapshot: async (id: string): Promise<{ kpi: Kpi; releaseId: string | null }> => {
    const response = await fetch(`${base()}/kpis/${encodeURIComponent(id)}`, { ...noStore, headers: { Accept: "application/json" } });
    return { kpi: await parse<Kpi>(response), releaseId: response.headers.get("x-odb-release") };
  },
  map: (
    kpi: string,
    p: {
      level: string;
      period?: string | null;
      within?: string | null;
      grain?: string | null;
      correction?: string | null;
      categories?: readonly string[];
      /** Vários períodos e acumulado (ADR-0026). */
      periods?: readonly string[];
      accumulate?: boolean | null;
    },
  ) =>
    get<MapData>(`/kpis/${encodeURIComponent(kpi)}/map${query(p)}`),
  detail: (
    kpi: string,
    p: {
      geography: string;
      period?: string | null;
      dimensions: readonly string[];
      grain?: string | null;
      correction?: string | null;
      categories?: readonly string[];
      periods?: readonly string[];
      accumulate?: boolean | null;
    },
  ) =>
    get<Detail>(`/kpis/${encodeURIComponent(kpi)}/detail${query(p)}`),
  series: (
    kpi: string,
    p: {
      geography: string;
      dimensions: readonly string[];
      grain?: string | null;
      correction?: string | null;
      categories?: readonly string[];
      /** Só os pontos contidos nesses períodos (ex.: os anos isolados). */
      periods?: readonly string[];
      accumulate?: "running" | "year" | null;
    },
  ) =>
    get<Series>(`/kpis/${encodeURIComponent(kpi)}/series${query(p)}`),
  table: (
    kpi: string,
    p: {
      level: string;
      period?: string | null;
      within?: string | null;
      dimensions: readonly string[];
      sort: "value" | "name";
      order: "asc" | "desc";
      offset: number;
      /** Território a localizar: a API devolve a página que o contém. */
      locate?: string | null;
      limit: number;
      grain?: string | null;
      correction?: string | null;
      categories?: readonly string[];
      periods?: readonly string[];
      accumulate?: "total" | "running" | "year" | null;
    },
  ) => get<Table>(`/kpis/${encodeURIComponent(kpi)}/table${query(p)}`),
  /** Série completa de um território em todos os grãos pedidos (B5). */
  history: (
    kpi: string,
    p: {
      geography: string;
      dimensions: readonly string[];
      grains?: readonly string[];
      correction?: string | null;
      categories?: readonly string[];
    },
  ) => get<History>(`/kpis/${encodeURIComponent(kpi)}/history${query(p)}`),
  /** Tabela dinâmica (B6): campos nas linhas e nas colunas. */
  pivot: (
    kpi: string,
    p: {
      level: string;
      within?: string | null;
      rows: readonly string[];
      cols: readonly string[];
      /** Períodos da tabela (DS 2.9: os do filtro Período); vazio: todos. */
      periods?: readonly string[];
      grain?: string | null;
      correction?: string | null;
      categories?: readonly string[];
    },
  ) => get<Pivot>(`/kpis/${encodeURIComponent(kpi)}/pivot${query(p)}`),
  details: (id: string, p: { level: string; within?: string | null; period?: string | null; dimensions: readonly string[]; grain?: string | null; correction?: string | null; categories?: readonly string[]; periods?: readonly string[]; accumulate?: boolean | null }) =>
    get<Detail[]>(`/kpis/${encodeURIComponent(id)}/details${query({ ...p, geography: undefined })}`),
  geographies: (level: string) => get<Geography[]>(`/geographies${query({ level, limit: 500 })}`),
  exportOptions: (id: string, within: string | null) =>
    get<ExportOptions>(`/kpis/${encodeURIComponent(id)}/export-options${query({ within })}`),
  geography: (key: string) => get<Geography>(`/geographies/${encodeURIComponent(key)}`),
  geometry: (level: string, within?: string | null) =>
    get<GeoCollection>(`/geometries/${encodeURIComponent(level)}${query({ within })}`),
  /**
   * Métricas de acesso (ADR-0027). Antes de a coleta existir a API responde 404; aqui isso
   * vira `null`, e a página diz que a coleta ainda não começou (nunca mostra zero).
   */
  metricsSummary: (period: PeriodRequest) => orNull(get<MetricsSummary>(`/metrics/summary${query(periodParams(period))}`)),
  metricsGeo: (level: GeoLevel, within: string | null, period: PeriodRequest) =>
    orNull(get<GeoResponse>(`/metrics/geo${query({ level, within, ...periodParams(period) })}`)),
  metricsDatasets: (sort: DatasetSort, period: PeriodRequest, limit = 10) =>
    orNull(get<DatasetsResponse>(`/metrics/datasets${query({ sort, limit, ...periodParams(period) })}`)),
  async exportFile(body: {
    kpi_id: string;
    level: string;
    within?: string | null;
    periods: string[];
    periods_by_grain?: Partial<Record<"mes" | "trimestre" | "semestre" | "ano", string[]>>;
    dimensions: string[];
    grain?: "mes" | "trimestre" | "semestre" | "ano" | null;
    correction?: string | null;
    categories?: string[];
    /** Janela de exportação (B5): vários níveis e grãos num arquivo; nunca acumulado. */
    levels?: string[];
    grains?: ("mes" | "trimestre" | "semestre" | "ano")[];
    format: ExportFormat;
  }): Promise<{ blob: Blob; filename: string }> {
    const response = await fetch(`${base()}/exports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) await parse(response);
    const disposition = response.headers.get("content-disposition") ?? "";
    const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? `exportacao.${body.format}`;
    return { blob: await response.blob(), filename };
  },
};
