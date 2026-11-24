// Formatos do bloco Contas públicas (briefing, seção 5). Valores nominais em R$.
const brlFull = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const one = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** R$ completo: "R$ 2.026.675.609,95" (tabela, tooltip, ficha). */
export function brl(value: number): string {
  return brlFull.format(value).replace(/ /g, " ");
}

/** R$ abreviado: "R$ 25,7 bi", "R$ 812,0 mi", "R$ 45,6 mil" (mapa, cartões, eixos). */
export function brlShort(value: number): string {
  const a = Math.abs(value);
  if (a >= 1e9) return `R$ ${one.format(value / 1e9)} bi`;
  if (a >= 1e6) return `R$ ${one.format(value / 1e6)} mi`;
  if (a >= 1e3) return `R$ ${one.format(value / 1e3)} mil`;
  return brl(value);
}

/** Participação vinda da API como fração (0–1): "39,1%". Nunca calculada aqui. */
export function share(fraction: number | null | undefined): string {
  return fraction === null || fraction === undefined ? "" : `${pct.format(fraction * 100)}%`;
}

/** Período da API: "2025" → "2025"; "2025M03" → "mar/2025"; "2025T1" → "1º tri/2025". */
export function periodLabel(code: string): string {
  const m = /^(\d{4})M(\d{2})$/.exec(code);
  if (m) return `${MONTHS[Number(m[2]) - 1]}/${m[1]}`;
  const q = /^(\d{4})T([1-4])$/.exec(code);
  if (q) return `${q[2]}º tri/${q[1]}`;
  return code;
}

/** Intervalo dos períodos da proveniência: "jan/2025 a dez/2025" ou "2025" quando é o ano inteiro. */
export function periodsLabel(periods: readonly string[]): string {
  if (!periods.length) return "";
  const first = periods[0] as string;
  const last = periods[periods.length - 1] as string;
  const year = first.slice(0, 4);
  if (periods.length === 12 && first === `${year}M01` && last === `${year}M12`) return year;
  return first === last ? periodLabel(first) : `${periodLabel(first)} a ${periodLabel(last)}`;
}

/** Nome da sede: "JOÃO PESSOA/PB". Sem sede, "—". */
export function seat(municipality: string | null | undefined, uf: string | null | undefined): string {
  if (!municipality && !uf) return "—";
  return [municipality, uf].filter(Boolean).join("/");
}
