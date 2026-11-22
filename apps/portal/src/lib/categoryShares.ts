import type { Pivot } from "./types";

export type ShareBasis = "published_total" | "published_group" | "displayed_sum" | "none";
export type SharePolicies = Readonly<Record<string, ShareBasis>>;
const SEP = "\u0001";
export const cellKey = (rows: readonly string[], cols: readonly string[]) =>
  `${rows.join(SEP)}\u0002${cols.join(SEP)}`;

/** Bases por grupo de irmãos; Total e subtotais não entram novamente na soma. */
export function compositionBases(
  data: Pivot,
  totals: Readonly<Record<string, string>>,
  policies: SharePolicies,
): Map<string, Map<string, number | null>> {
  const fields = [
    ...data.row_fields.map((field, index) => ({ id: field.id, index, side: "row" })),
    ...data.col_fields.map((field, index) => ({ id: field.id, index, side: "col" })),
  ].filter((field) => policies[field.id] === "displayed_sum" && totals[field.id]);
  const result = new Map(fields.map((field) => [field.id, new Map<string, number | null>()]));
  data.rows.forEach((row, i) => data.columns.forEach((col, j) => {
    const cell = data.cells[i]?.[j];
    if (!cell) return; // Cruzamento inexistente neste período não é um zero ou valor sob sigilo.
    const value = cell.value;
    for (const field of fields) {
      const selected = field.side === "row" ? row.keys[field.index] : col.keys[field.index];
      if (selected === totals[field.id]) continue;
      const rows = [...row.keys];
      const cols = [...col.keys];
      if (field.side === "row") rows[field.index] = totals[field.id]!;
      else cols[field.index] = totals[field.id]!;
      const group = cellKey(rows, cols);
      const values = result.get(field.id)!;
      const previous = values.get(group);
      values.set(group, previous === null || value == null || !Number.isFinite(value) || value < 0
        ? null : (previous ?? 0) + value);
    }
  }));
  return result;
}

/** Última dimensão efetivamente detalhada, na hierarquia do KPI, em qualquer eixo. */
export function percentageDimension(
  rowFields: readonly string[], colFields: readonly string[],
  rows: readonly string[], cols: readonly string[],
  totals: Readonly<Record<string, string>>, order: readonly string[],
): string | null {
  const slots = [...rowFields.map((id, i) => [id, rows[i]]), ...colFields.map((id, i) => [id, cols[i]])];
  const fields = order.filter((id) => slots.some(([field]) => field === id) && totals[id]);
  return [...fields].reverse().find((id) =>
    slots.some(([field, value]) => field === id && value !== totals[id]),
  ) ?? fields[0] ?? null;
}
