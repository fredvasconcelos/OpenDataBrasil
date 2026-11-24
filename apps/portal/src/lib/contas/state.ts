import type { ContasMeta } from "./types";
import type { Geography } from "@/lib/types";

const PANEL_PATH = "/contas/painel";
const PANEL_FIELDS = ["geography", "period", "area", "page", "grain"] as const;

/** Guarda apenas os filtros do painel ao abrir uma ficha, sem aceitar destino externo. */
export function panelHref(params: URLSearchParams): string {
  const kept = new URLSearchParams();
  for (const field of PANEL_FIELDS) {
    const value = params.get(field);
    if (value) kept.set(field, value);
  }
  return `${PANEL_PATH}${kept.size ? `?${kept}` : ""}`;
}

/** Restringe o retorno da ficha à rota das contas e aos seus parâmetros conhecidos. */
export function safePanelHref(value: string | string[] | undefined): string {
  if (typeof value !== "string" || !(value === PANEL_PATH || value.startsWith(`${PANEL_PATH}?`))) return PANEL_PATH;
  return panelHref(new URL(value, "https://portal.invalid").searchParams);
}

/** Segue a hierarquia oficial: o pai imediato de um município pode ser uma região. */
export async function findState(geography: Geography, load: (key: string) => Promise<Geography>): Promise<Geography | null> {
  let current = geography;
  const seen = new Set<string>();
  while (current.parent_key && !seen.has(current.geography_key)) {
    if (current.level_id === "uf") return current;
    seen.add(current.geography_key);
    current = await load(current.parent_key);
  }
  return current.level_id === "uf" ? current : null;
}

/** Oferece somente anos e meses presentes nos metadados oficiais do release. */
export function availablePeriods(meta: ContasMeta): string[] {
  const months = meta.lenses.find((l) => l.lens === "A")?.periods ?? [];
  return [...new Set(months.map((p) => p.slice(0, 4)))].reverse().flatMap((year) => [year, ...months.filter((p) => p.startsWith(year)).toReversed()]);
}

/** Prefere o último ano integral fechado; sem ele, o último mês disponível. */
export function defaultPeriod(meta: ContasMeta): string {
  const lens = meta.lenses.find((l) => l.lens === "A");
  const years = [...new Set(lens?.periods.map((p) => p.slice(0, 4)) ?? [])].toReversed();
  const closed = new Set(lens?.statuses.filter((s) => s.status === "fechado").map((s) => s.period));
  return years.find((year) => Array.from({ length: 12 }, (_, i) => `${year}M${String(i + 1).padStart(2, "0")}`).every((p) => closed.has(p))) ?? lens?.latest_period ?? "";
}

/** Estado de apresentação; disponibilidade e validade estatística continuam na API. */
export function readContasState(search: URLSearchParams, meta: ContasMeta) {
  const requested = search.get("period");
  const period = requested && availablePeriods(meta).includes(requested) ? requested : defaultPeriod(meta);
  const page = Number(search.get("page") ?? "1");
  return {
    geography: search.get("geography") ?? "brasil:1",
    period,
    area: search.get("area") || null,
    page: Number.isInteger(page) && page >= 1 && page <= 100 ? page : 1,
    grain: search.get("grain") === "ano" ? "ano" as const : "mes" as const,
  };
}
