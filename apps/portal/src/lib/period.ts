// Períodos da série temporal (Design System ODBr, seção 9 · Séries).
// O eixo X do gráfico é de TEMPO, não de categorias: anos ausentes (ex.: 2010 e 2022
// na PNAD) deixam um vão proporcional em vez de serem "colados" aos vizinhos, e os
// rótulos do eixo saem em passos redondos (1, 2, 5, 10… anos) que cabem na largura.
//
// Códigos aceitos (como chegam da API / SIDRA):
//   "2020"                     → ano
//   "202003" · "2020-03"       → mês (março de 2020)
//   "2020M03"                  → mês, como a Gold do projeto grava (AAAAMmm)
//   "2020T1" · "2020-Q1"       → trimestre
//   "2020S1"                   → semestre (soma dos meses na Gold, ADR-0013)
//   "202001"…"202004"          → trimestre, SÓ quando todos os códigos de 6 dígitos da
//                                série terminam em 01–04 e cobrem mais de um ano
//                                (heurística; passe `hint` quando a fonte informar).
// Se qualquer código não for reconhecido, `parsePeriods` devolve null e o gráfico usa
// o eixo ordinal (um passo por período, na ordem do texto).

export type Granularity = "year" | "semester" | "quarter" | "month";

export interface ParsedPeriod {
  raw: string;
  granularity: Granularity;
  /** Índice inteiro na unidade da granularidade (ano; ano·4 + tri − 1; ano·12 + mês − 1). */
  unit: number;
  /** Tempo decimal em anos (2020,25 = abril de 2020), usado na escala do eixo. */
  t: number;
}

const PER_YEAR: Record<Granularity, number> = { year: 1, semester: 2, quarter: 4, month: 12 };
const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

const YEAR = /^(\d{4})$/;
const MONTH = /^(\d{4})(?:-|M)?(0[1-9]|1[0-2])$/;
const QUARTER = /^(\d{4})-?(?:T|Q)([1-4])$/i;
const SEMESTER = /^(\d{4})-?S([12])$/i;
const SIX = /^(\d{4})(\d{2})$/;

function make(raw: string, granularity: Granularity, year: number, index = 1): ParsedPeriod {
  const k = PER_YEAR[granularity];
  const unit = year * k + (index - 1);
  return { raw, granularity, unit, t: unit / k };
}

/** Os códigos de 6 dígitos desta lista parecem trimestres (01–04 em mais de um ano)? */
function looksQuarterly(raws: readonly string[]): boolean {
  const six = raws.map((r) => SIX.exec(r)).filter((m): m is RegExpExecArray => m !== null);
  if (!six.length) return false;
  const years = new Set(six.map((m) => m[1]));
  return years.size > 1 && six.every((m) => Number(m[2]) >= 1 && Number(m[2]) <= 4);
}

export function parsePeriod(raw: string, hint?: Granularity): ParsedPeriod | null {
  const s = raw.trim();
  let m = YEAR.exec(s);
  if (m) return make(raw, "year", Number(m[1]));
  m = QUARTER.exec(s);
  if (m) return make(raw, "quarter", Number(m[1]), Number(m[2]));
  m = SEMESTER.exec(s);
  if (m) return make(raw, "semester", Number(m[1]), Number(m[2]));
  if (hint === "quarter") {
    m = SIX.exec(s);
    if (m && Number(m[2]) >= 1 && Number(m[2]) <= 4) return make(raw, "quarter", Number(m[1]), Number(m[2]));
    return null;
  }
  m = MONTH.exec(s);
  if (m) return make(raw, "month", Number(m[1]), Number(m[2]));
  return null;
}

/**
 * Lê todos os períodos de uma série. Devolve null se algum código não for reconhecido
 * ou se a lista misturar granularidades (o gráfico cai no eixo ordinal).
 */
export function parsePeriods(raws: readonly string[], hint?: Granularity): ParsedPeriod[] | null {
  const effective = hint ?? (looksQuarterly(raws) ? "quarter" : undefined);
  const out: ParsedPeriod[] = [];
  for (const raw of raws) {
    const p = parsePeriod(raw, effective);
    if (!p) return null;
    out.push(p);
  }
  if (new Set(out.map((p) => p.granularity)).size > 1) return null;
  return out.sort((a, b) => a.unit - b.unit);
}

function split(p: Pick<ParsedPeriod, "granularity" | "unit">): { year: number; index: number } {
  const k = PER_YEAR[p.granularity];
  return { year: Math.floor(p.unit / k), index: (p.unit % k) + 1 };
}

/**
 * Rótulo do período, para o tooltip, os seletores e a leitura de tela: "2020", "mar 2020",
 * "T1 2020" e "S1 2020" (decisão do mantenedor, ADR-0013: os mesmos rótulos abreviados da
 * dim_period da Gold).
 */
export function formatPeriod(p: Pick<ParsedPeriod, "granularity" | "unit">): string {
  const { year, index } = split(p);
  if (p.granularity === "month") return `${MONTHS[index - 1]} ${year}`;
  if (p.granularity === "quarter") return `T${index} ${year}`;
  if (p.granularity === "semester") return `S${index} ${year}`;
  return String(year);
}

/** Rótulo do eixo: só o ano quando o passo é de um ano ou mais e o tick cai no início do ano. */
export function formatTick(p: Pick<ParsedPeriod, "granularity" | "unit">, stepUnits: number): string {
  const k = PER_YEAR[p.granularity];
  const { year, index } = split(p);
  if (k > 1 && stepUnits >= k && index === 1) return String(year);
  return formatPeriod(p);
}

const STEPS: Record<Granularity, number[]> = {
  year: [1, 2, 5, 10, 20, 25, 50, 100],
  semester: [1, 2, 4, 10, 20, 50],
  quarter: [1, 2, 4, 8, 20, 40, 100],
  month: [1, 2, 3, 6, 12, 24, 60, 120, 240],
};

export interface Tick {
  unit: number;
  t: number;
  label: string;
  /** Âncora do texto: a primeira e a última ficam dentro do gráfico. */
  anchor: "start" | "middle" | "end";
}

/** Largura aproximada de um rótulo em Nunito 12/700 (px). */
export const labelWidth = (text: string) => Math.ceil(text.length * 7.2);

/**
 * Escolhe os rótulos do eixo X de tempo: o menor passo redondo cujos rótulos cabem na
 * largura útil, mais as duas pontas da série (primeiro e último período publicados).
 * Ticks internos próximos demais das pontas são descartados para não encostar.
 */
export function timeTicks(
  periods: readonly ParsedPeriod[],
  innerWidth: number,
  toX: (t: number) => number,
  gap = 16,
): { ticks: Tick[]; step: number } {
  if (!periods.length) return { ticks: [], step: 1 };
  const first = periods[0] as ParsedPeriod;
  const last = periods[periods.length - 1] as ParsedPeriod;
  const g = first.granularity;
  const k = PER_YEAR[g];
  const span = last.unit - first.unit;
  const at = (unit: number) => ({ granularity: g, unit });
  const sample = formatPeriod(last);
  const room = Math.max(1, Math.floor(innerWidth / (labelWidth(sample) + gap)));

  let step = STEPS[g][STEPS[g].length - 1] as number;
  for (const s of STEPS[g]) {
    if (span / s + 1 <= room) {
      step = s;
      break;
    }
  }

  const ends: Tick[] = [{ unit: first.unit, t: first.t, label: formatPeriod(first), anchor: "start" }];
  if (last.unit !== first.unit) ends.push({ unit: last.unit, t: last.t, label: formatPeriod(last), anchor: "end" });
  // Passos a partir de um ano: alinhados ao início do ano (2005, 2010…; jan de cada ano).
  // Os passos de STEPS a partir de k são múltiplos de k, então caem sempre no início do ano.
  const startUnit = Math.ceil((first.unit + 1) / step) * step;
  const inner: Tick[] = [];
  for (let u = startUnit; u < last.unit; u += step) {
    inner.push({ unit: u, t: u / k, label: formatTick(at(u), step), anchor: "middle" });
  }

  const half = (tick: Tick) => labelWidth(tick.label) / 2;
  const fstX = toX(first.t) + labelWidth(ends[0]!.label);
  const lstX = ends[1] ? toX(last.t) - labelWidth(ends[1].label) : Infinity;
  const kept = inner.filter((tick) => {
    const x = toX(tick.t);
    return x - half(tick) >= fstX + gap / 2 && x + half(tick) <= lstX - gap / 2;
  });
  const ticks = [ends[0]!, ...kept, ...(ends[1] ? [ends[1]] : [])];
  return { ticks, step };
}

/**
 * Passo típico da série (mediana entre períodos consecutivos, em unidades). Saltos
 * maiores que 1,5× esse passo são "períodos não publicados" e viram traço pontilhado.
 */
export function typicalStep(periods: readonly ParsedPeriod[]): number {
  const diffs: number[] = [];
  for (let i = 1; i < periods.length; i++) diffs.push((periods[i] as ParsedPeriod).unit - (periods[i - 1] as ParsedPeriod).unit);
  if (!diffs.length) return 1;
  diffs.sort((a, b) => a - b);
  return diffs[Math.floor(diffs.length / 2)] as number;
}

// ---------------------------------------------------------------- eixo agrupado (v2.3.2)

/** As partes do ano ("T4", "S2") cabem numa fatia de `slot` px? */
export function partsFit(slot: number, granularity: Granularity, gap = 8): boolean {
  const k = PER_YEAR[granularity];
  return slot >= labelWidth(`${granularity === "quarter" ? "T" : "S"}${k}`) + gap;
}

/** Fatia de um período (px) numa largura útil, pelo intervalo da série. */
export function slotWidth(periods: readonly ParsedPeriod[], width: number): number {
  const first = periods[0];
  const last = periods[periods.length - 1];
  return first && last ? width / Math.max(1, last.unit - first.unit) : width;
}

/** Granularidades com eixo em duas linhas: a parte do ano em cima e o ano embaixo. */
export const GROUPED: readonly Granularity[] = ["quarter", "semester"];

export interface GroupedAxis {
  /** Rótulos de cima ("T1"…"T4", "S1"/"S2"), um por período do intervalo; vazio sem espaço. */
  parts: { x: number; label: string }[];
  /** Ano centralizado sob o grupo; `label` vazio quando o passo pula o ano. */
  years: { x: number; label: string }[];
  /** Divisórias entre anos (posição x). */
  bounds: number[];
}

/**
 * Eixo de trimestres ou semestres em duas linhas: em cima a parte do ano, embaixo o ano,
 * centralizado no trecho que os períodos dele ocupam, com divisórias entre os anos.
 * As partes só aparecem se couberem todas; os anos, num passo redondo (1, 2, 5, 10…)
 * que caiba. `toX` recebe o tempo decimal (2026,5 = julho de 2026).
 */
export function groupedAxis(
  periods: readonly ParsedPeriod[],
  x0: number,
  x1: number,
  toX: (t: number) => number,
  gap = 8,
  withParts = true,
): GroupedAxis {
  const empty: GroupedAxis = { parts: [], years: [], bounds: [] };
  const first = periods[0];
  const last = periods[periods.length - 1];
  if (!first || !last || !GROUPED.includes(first.granularity)) return empty;
  const g = first.granularity;
  const k = PER_YEAR[g];
  const prefix = g === "quarter" ? "T" : "S";
  const slot = Math.abs(toX(first.t + 1 / k) - toX(first.t));
  const units = Array.from({ length: last.unit - first.unit + 1 }, (_, i) => first.unit + i);
  const fits = withParts && partsFit(slot, g, gap);
  const parts = fits ? units.map((u) => ({ x: toX(u / k), label: `${prefix}${(u % k) + 1}` })) : [];

  const firstYear = Math.floor(first.unit / k);
  const lastYear = Math.floor(last.unit / k);
  const spans: { year: number; from: number; to: number }[] = [];
  for (let yr = firstYear; yr <= lastYear; yr++) {
    const a = Math.max(first.unit, yr * k);
    const b = Math.min(last.unit, yr * k + k - 1);
    spans.push({ year: yr, from: toX(a / k) - slot / 2, to: toX(b / k) + slot / 2 });
  }
  // Ano com 4 dígitos se couber em todos os grupos; senão, com 2 ("26", pedido do
  // mantenedor), desde que a série não atravesse a virada do século ("97" e "26" seriam
  // ambíguos). Ainda sem espaço, os anos seguem um passo redondo.
  const widest = Math.max(...spans.map((sp) => sp.to - sp.from));
  const sameCentury = Math.floor(firstYear / 100) === Math.floor(lastYear / 100);
  const short = widest < labelWidth("2026") + gap && sameCentury;
  const yearText = (yr: number) => (short ? String(yr % 100).padStart(2, "0") : String(yr));
  const yearWidth = labelWidth(short ? "26" : "2026");
  const yearStep = [1, 2, 5, 10, 20, 50].find((st) => widest * st >= yearWidth + gap) ?? 50;
  // Centro do trecho do ano, mantendo o rótulo inteiro dentro do gráfico.
  const inside = (x: number) => Math.min(x1 - yearWidth / 2, Math.max(x0 + yearWidth / 2, x));
  // Da esquerda para a direita: o ano que encostaria no anterior fica sem rótulo
  // (ex.: o ano corrente com só dois trimestres, empurrado para dentro do gráfico).
  let right = -Infinity;
  const years = spans.map((sp) => {
    const x = inside((sp.from + sp.to) / 2);
    const show = (sp.year - firstYear) % yearStep === 0 && x - yearWidth / 2 >= right + gap;
    if (show) right = x + yearWidth / 2;
    return { x, label: show ? yearText(sp.year) : "" };
  });
  const bounds = spans.slice(1).map((sp) => sp.from);
  return { parts, years, bounds };
}
