// Página Métricas (ADR-0027, DS 2.12): contratos dos endpoints /metrics/* e regras puras
// (formatação pt-BR, cores por quantis, Grandes Regiões, árvore do ranking e período).
// Sem cookies: só visualizações, aberturas de indicador e downloads; nunca "visitantes".
import { quantileScale } from "./scale";
import { SEQ, ZERO_COLOR } from "./theme";

export type GeoLevel = "pais" | "regiao" | "uf";
export type GeoStatus = "ok" | "suprimido" | "sem_acessos";
export type PeriodKey = "7d" | "30d" | "12m" | "custom";
export type DatasetSort = "views" | "downloads";

export interface PeriodRange {
  from: string;
  to: string;
}

export interface MetricsSummary {
  period: PeriodRange;
  generated_at: string;
  collection_started_at: string | null;
  views: number;
  kpi_opens: number;
  downloads: number;
  countries: number;
  /** `null`: não coletado (ainda não há API pública). Diferente de zero. */
  api_calls: number | null;
}

export interface GeoItem {
  geography_key: string;
  name: string;
  /** `null` quando suprimido (de 1 a 4 visualizações). */
  views: number | null;
  share_pct: number | null;
  status: GeoStatus;
}

export interface GeoResponse {
  level: GeoLevel;
  within: string | null;
  period: PeriodRange;
  items: GeoItem[];
}

export interface DatasetItem {
  kpi_id: string;
  title: string;
  theme: string;
  views: number;
  downloads: number;
  api_calls: number | null;
}

export interface DatasetsResponse {
  sort: DatasetSort;
  period: PeriodRange;
  items: DatasetItem[];
}

/** Período pedido à API: um atalho, ou "custom" com as duas datas (AAAA-MM-DD). */
export type PeriodRequest = { period: Exclude<PeriodKey, "custom"> | "all" } | { period: "custom"; from: string; to: string };

export const PERIOD_KEYS: readonly PeriodKey[] = ["7d", "30d", "12m", "custom"];
/** Maior intervalo personalizado aceito pela API (ADR-0027, item 7). */
export const MAX_CUSTOM_DAYS = 366;
/** Abaixo disto a API suprime o número (ADR-0027, limiar confirmado). */
export const SUPPRESSION_THRESHOLD = 5;

const nf = new Intl.NumberFormat("pt-BR");
const pf = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Contagem em formato brasileiro (12.345). */
export function formatCount(value: number): string {
  return nf.format(value);
}

/** Percentual com uma casa (12,3%). */
export function formatPct(value: number): string {
  return `${pf.format(value)}%`;
}

const dayFmt = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

function asDate(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

/** "18 de out. de 2026 – 16 de nov. de 2026", a partir de datas AAAA-MM-DD. */
export function formatRange(range: PeriodRange): string {
  const a = dayFmt.format(asDate(range.from));
  const b = dayFmt.format(asDate(range.to));
  return a === b ? a : `${a} – ${b}`;
}

/** Erro do período personalizado, ou null quando válido. */
export function customRangeError(from: string, to: string): "missing" | "order" | "length" | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(from) || !/^\d{4}-\d{2}-\d{2}$/.test(to)) return "missing";
  const a = asDate(from).getTime();
  const b = asDate(to).getTime();
  if (Number.isNaN(a) || Number.isNaN(b)) return "missing";
  if (a > b) return "order";
  if ((b - a) / 86_400_000 + 1 > MAX_CUSTOM_DAYS) return "length";
  return null;
}

/** Parâmetros de consulta do período. */
export function periodParams(p: PeriodRequest): Record<string, string> {
  return p.period === "custom" ? { period: "custom", from: p.from, to: p.to } : { period: p.period };
}

// Grandes Regiões: o 1º dígito do código IBGE da UF (11 a 17 → 1, Norte etc.).
export const REGIONS: Readonly<Record<string, { name: string; abbr: string }>> = {
  "regiao:1": { name: "Norte", abbr: "N" },
  "regiao:2": { name: "Nordeste", abbr: "NE" },
  "regiao:3": { name: "Sudeste", abbr: "SE" },
  "regiao:4": { name: "Sul", abbr: "S" },
  "regiao:5": { name: "Centro-Oeste", abbr: "CO" },
};

/** "uf:35" → "regiao:3"; null para chaves que não são de UF. */
export function regionOfUf(key: string): string | null {
  const m = /^uf:([1-5])\d$/.exec(key);
  return m ? `regiao:${m[1]}` : null;
}

/** Cor do território: quantis sobre os valores publicados; zero e suprimido à parte. */
export function geoColors(items: readonly GeoItem[]): { color: (item: GeoItem) => string; scale: ReturnType<typeof quantileScale> } {
  const scale = quantileScale(items.filter((i) => i.status === "ok").map((i) => i.views));
  return {
    scale,
    color: (item) => {
      if (item.status === "sem_acessos") return ZERO_COLOR;
      // De 1 a 4 visualizações: o tom mais claro da escala, sem número.
      if (item.status === "suprimido" || item.views === null) return SEQ[0] as string;
      return scale.color(item.views);
    },
  };
}

export interface ValueLabels {
  /** "sem acessos" */
  noAccess: string;
  /** "menos de 5" */
  lessThan: string;
}

/** Texto do valor de um lugar (para tooltip, ranking e tabela). */
export function viewsText(item: Pick<GeoItem, "views" | "status">, labels: ValueLabels): string {
  if (item.status === "sem_acessos") return labels.noAccess;
  if (item.status === "suprimido" || item.views === null) return labels.lessThan;
  return formatCount(item.views);
}

export interface RankNode {
  key: string;
  name: string;
  item: GeoItem;
  children: RankNode[];
}

/** Ordem do ranking: mais visualizações primeiro; suprimidos e zeros no fim, por nome. */
function byViews(a: RankNode, b: RankNode): number {
  const va = a.item.status === "ok" ? (a.item.views ?? 0) : a.item.status === "suprimido" ? 0.5 : 0;
  const vb = b.item.status === "ok" ? (b.item.views ?? 0) : b.item.status === "suprimido" ? 0.5 : 0;
  return vb - va || a.name.localeCompare(b.name, "pt-BR");
}

/**
 * Árvore País › Grande Região › Estado. As regiões ficam sob o Brasil e cada UF sob a
 * região do 1º dígito do código. Lugares sem nível acima (UF sem região conhecida) não
 * entram, para não somar errado.
 */
export function buildRankingTree(
  countries: readonly GeoItem[],
  regions: readonly GeoItem[],
  ufs: readonly GeoItem[],
): RankNode[] {
  const regionNodes = regions.map<RankNode>((r) => ({ key: r.geography_key, name: r.name, item: r, children: [] }));
  for (const uf of ufs) {
    const parent = regionNodes.find((r) => r.key === regionOfUf(uf.geography_key));
    if (parent) parent.children.push({ key: uf.geography_key, name: uf.name, item: uf, children: [] });
  }
  for (const r of regionNodes) r.children.sort(byViews);
  const roots = countries.map<RankNode>((c) => ({
    key: c.geography_key,
    name: c.name,
    item: c,
    children: c.geography_key === "pais:BR" ? [...regionNodes].sort(byViews) : [],
  }));
  return roots.sort(byViews);
}

/** Caminho da raiz até a chave (para abrir a árvore no lugar escolhido no mapa). */
export function pathTo(nodes: readonly RankNode[], key: string): string[] {
  for (const n of nodes) {
    if (n.key === key) return [n.key];
    const sub = pathTo(n.children, key);
    if (sub.length) return [n.key, ...sub];
  }
  return [];
}
