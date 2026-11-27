import type { ContasLens, ContasMeta } from "./types";
import type { Geography } from "@/lib/types";

const PANEL_PATH = "/contas/painel";
const PANEL_FIELDS = ["lens", "geography", "period", "area", "page", "grain", "order", "group"] as const;

/** Guarda apenas os filtros do painel ao abrir uma ficha, sem aceitar destino externo. */
export function panelHref(params: URLSearchParams): string {
  const kept = new URLSearchParams();
  for (const field of PANEL_FIELDS) {
    const value = params.get(field);
    if (value) kept.set(field, value);
  }
  for (const filter of params.getAll("filter")) kept.append("filter", filter);
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
export function availablePeriods(meta: ContasMeta, selected: ContasLens = "A"): string[] {
  const months = meta.lenses.find((l) => l.lens === selected)?.periods ?? [];
  return [...new Set(months.map((p) => p.slice(0, 4)))].reverse().flatMap((year) => [year, ...months.filter((p) => p.startsWith(year)).toReversed()]);
}

/** Prefere o último ano integral fechado; sem ele, o último mês disponível. */
export function defaultPeriod(meta: ContasMeta, selected: ContasLens = "A"): string {
  const lens = meta.lenses.find((l) => l.lens === selected);
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
    // Ordem da tabela de recebedores; a API ordena por valor (padrão) ou por nome.
    order: search.get("order") === "name" ? "name" as const : "value" as const,
  };
}

/** Os grupos, calendários e filtros pertencem à lente, nunca são herdados de outra. */
export function readFederalState(search: URLSearchParams, meta: ContasMeta, lens: "B" | "C") {
  const definition = meta.lenses.find((item) => item.lens === lens);
  const groups = lens === "C" ? definition?.dimensions.map((d) => d.id) ?? [] : definition?.group_by.filter((d) => d.id !== "territory" || !search.get("geography")?.startsWith("municipio:")).map((d) => d.id) ?? [];
  const requestedGroup = search.get("group") ?? "";
  const group = groups.includes(requestedGroup) ? requestedGroup : lens === "C" ? "function" : "recipient";
  const requestedPeriod = search.get("period") ?? "";
  const period = availablePeriods(meta, lens).includes(requestedPeriod) ? requestedPeriod : defaultPeriod(meta, lens);
  const requestedPage = Number(search.get("page") ?? 1);
  const page = Number.isInteger(requestedPage) && requestedPage >= 1 && requestedPage <= 100 ? requestedPage : 1;
  // O contrato aceita dez dimensões; uma categoria por dimensão evita filtros contraditórios.
  const filters = [...new Map(search.getAll("filter").filter((item) => {
    const at = item.indexOf(":");
    return at > 0 && (definition?.dimensions.map((d) => d.id) ?? []).includes(item.slice(0, at)) && /^[^,\u0000-\u001f]{1,4096}$/.test(item.slice(at + 1));
  }).map((item) => [item.slice(0, item.indexOf(":")), item])).values()].slice(0, 10);
  return { group, period, page, filters, geography: search.get("geography") || "brasil:1" };
}
