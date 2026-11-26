// Cliente do bloco 2 sobre o contrato completo gerado. Não compartilha o cache dos KPIs.
import { ApiRequestError } from "@/lib/api";
import type { ContasComposition, ContasMap, ContasMeta, ContasRanking, ContasSeries, ContasTable, RecipientProfile } from "@/lib/contas/types";

type Params = Record<string, string | number | readonly string[] | null | undefined>;

/** Mantém parâmetros repetidos, como periods e categories, aceitos pela API das contas. */
export function contasQuery(params: Params): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    for (const item of Array.isArray(value) ? value : value == null ? [] : [String(value)]) {
      if (item !== "") query.append(key, item);
    }
  }
  return query.size ? `?${query}` : "";
}

async function get<T>(path: string, params: Params = {}): Promise<T> {
  const base = typeof window === "undefined"
    ? `${(process.env.ODB_API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "")}/api/v1`
    : "/odb-api";
  const response = await fetch(`${base}/contas/${path}${contasQuery(params)}`, { cache: "no-store", headers: { Accept: "application/json" } });
  if (!response.ok) throw new ApiRequestError(response.status, "contas_unavailable", "contas_unavailable");
  return await response.json() as T;
}

export const contasApi = {
  meta: () => get<ContasMeta>("meta"),
  map: (p: { level: "uf" | "municipio"; within?: string | null; periods: string[]; dimension?: string; categories?: string[] }) => get<ContasMap>("map", { ...p, lens: "A" }),
  composition: (geography: string, periods: string[]) => get<ContasComposition>("composition", { lens: "A", geography_key: geography, periods, dimension: "function", limit: 10 }),
  series: (p: { geography_key: string; periods: string[]; grain: "mes" | "ano"; dimension?: string; categories?: string[] }) => get<ContasSeries>("series", { ...p, lens: "A" }),
  ranking: (geography: string, year: number, page: number) => get<ContasRanking>("ranking", { lens: "A", geography_key: geography, year, page }),
  table: (p: { geography_key: string; periods: string[]; group_by: "function" | "transfer_type" | "recipient"; filter?: string[]; page?: number; sort?: "value" | "name" }) => get<ContasTable>("table", { ...p, lens: "A" }),
  /** Percorre a paginação oficial, sem esconder áreas num grupo de demais. */
  areas: async (geography: string, periods: string[]): Promise<ContasTable> => {
    const params = { geography_key: geography, periods, group_by: "function" as const };
    const first = await contasApi.table(params);
    const rows = [...first.rows];
    for (let page = 2; page <= first.pages; page++) {
      const next = await contasApi.table({ ...params, page });
      if (next.provenance.release_id !== first.provenance.release_id || next.rows_total !== first.rows_total) throw new Error("release_changed");
      rows.push(...next.rows);
    }
    if (rows.length !== first.rows_total || new Set(rows.map((r) => r.key)).size !== rows.length) throw new Error("incomplete_areas");
    return { ...first, rows };
  },
  recipient: (id: string, periods?: string[]) => get<RecipientProfile>(`favorecidos/${encodeURIComponent(id)}`, { periods }),
};
