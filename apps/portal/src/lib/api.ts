// Cliente da API. No navegador, as chamadas passam pelo proxy do próprio portal
// (/odb-api → API interna); no servidor, vão direto à URL interna.
import type {
  Dataset,
  Detail,
  ExportFormat,
  GeoCollection,
  Geography,
  Indicator,
  Kpi,
  MapData,
  Navigation,
  Release,
  Series,
  Table,
} from "./types";

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

type Params = Record<string, string | number | readonly string[] | null | undefined>;

export function query(params: Params): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
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

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  return parse<T>(await fetch(`${base()}${path}`, { ...init, headers: { Accept: "application/json" } }));
}

const noStore: RequestInit = { cache: "no-store" };

export const api = {
  navigation: () => get<Navigation>("/portal/navigation", noStore),
  release: () => get<Release>("/release", noStore),
  datasets: () => get<Dataset[]>("/datasets", noStore),
  indicators: (q?: string) => get<Indicator[]>(`/indicators${query({ q })}`, noStore),
  kpi: (id: string) => get<Kpi>(`/kpis/${encodeURIComponent(id)}`),
  map: (
    kpi: string,
    p: { level: string; period?: string | null; within?: string | null; grain?: string | null; correction?: string | null },
  ) =>
    get<MapData>(`/kpis/${encodeURIComponent(kpi)}/map${query(p)}`),
  detail: (
    kpi: string,
    p: { geography: string; period?: string | null; dimensions: readonly string[]; grain?: string | null; correction?: string | null },
  ) =>
    get<Detail>(`/kpis/${encodeURIComponent(kpi)}/detail${query(p)}`),
  series: (kpi: string, p: { geography: string; dimensions: readonly string[]; grain?: string | null; correction?: string | null }) =>
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
    },
  ) => get<Table>(`/kpis/${encodeURIComponent(kpi)}/table${query(p)}`),
  geography: (key: string) => get<Geography>(`/geographies/${encodeURIComponent(key)}`),
  geometry: (level: string, within?: string | null) =>
    get<GeoCollection>(`/geometries/${encodeURIComponent(level)}${query({ within })}`),
  async exportFile(body: {
    kpi_id: string;
    level: string;
    within?: string | null;
    periods: string[];
    dimensions: string[];
    grain?: "mes" | "trimestre" | "semestre" | "ano" | null;
    correction?: string | null;
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
