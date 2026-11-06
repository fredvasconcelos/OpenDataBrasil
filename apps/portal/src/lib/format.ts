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

export function formatShare(share: number | null | undefined): string {
  return share === null || share === undefined ? "" : `${percent.format(share)}%`;
}

export function unitSuffix(unit: string): string {
  if (unit === "%") return "%";
  if (unit === "Quilômetros quadrados") return "km²";
  if (unit === "Habitante por quilômetro quadrado") return "hab/km²";
  return unit.toLowerCase();
}
