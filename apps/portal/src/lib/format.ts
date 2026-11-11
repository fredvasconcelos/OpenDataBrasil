// Formatação de números e unidades em pt-BR. Valor ausente nunca vira zero.

const integer = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const compact = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const MISSING: Record<string, string> = {
  suppressed: "X (sigilo)",
  not_available: "…",
  not_applicable: "não se aplica",
  absent: "sem dado",
};

export function formatValue(value: number | null | undefined, status = "valid"): string {
  if (value === null || value === undefined) return MISSING[status] ?? "sem dado";
  return Number.isInteger(value) ? integer.format(value) : decimal.format(value);
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return Math.abs(value) < 10_000 ? formatValue(value) : compact.format(value);
}

const bound = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
const small = new Intl.NumberFormat("pt-BR", { maximumSignificantDigits: 3 });

/** Limite de grupo da legenda: "4 mil", "1,5 mil", "250", "0,25". */
export function formatBound(value: number): string {
  return Math.abs(value) >= 1000 ? bound.format(value) : small.format(value);
}

/** Chave da mensagem de título da legenda para a unidade do indicador. */
export function legendTitleKey(unit: string): "people" | "percent" | "density" | "area" | null {
  if (unit === "Pessoas") return "people";
  if (unit === "%") return "percent";
  if (unit === "Habitante por quilômetro quadrado") return "density";
  if (unit === "Quilômetros quadrados") return "area";
  return null;
}

export function formatShare(share: number | null | undefined): string {
  return share === null || share === undefined ? "" : `${percent.format(share)}%`;
}

export function unitSuffix(unit: string): string {
  if (unit === "%") return "%";
  if (unit === "Quilômetros quadrados") return "km²";
  if (unit === "Habitante por quilômetro quadrado") return "hab/km²";
  return unit.toLowerCase();
}

const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** Período da Gold para exibição: "2022", "2026M09" → "set/2026", "2026T2" → "2º tri/2026". */
export function formatPeriod(period: string): string {
  const month = /^(\d{4})M(0[1-9]|1[0-2])$/.exec(period);
  if (month) return `${MONTHS[Number(month[2]) - 1]}/${month[1]}`;
  const quarter = /^(\d{4})T([1-4])$/.exec(period);
  if (quarter) return `${quarter[2]}º tri/${quarter[1]}`;
  return period;
}
