import { cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import { compositionBases, percentageDimension } from "@/lib/categoryShares";
import type { Pivot } from "@/lib/types";
import { PivotTable } from "./PivotTable";

afterEach(cleanup);
const totals = { c339: "c339:7999", c12190: "c12190:103536" };
const policies = { c339: "displayed_sum", c12190: "published_group" } as const;
const incomes = [totals.c339, "c339:47558", "c339:47559", "c339:47560"];
const expenses = [totals.c12190, "c12190:103539", "c12190:103540", "c12190:103554"];

function fixture(): Pivot {
  return {
    kpi_id: "despesa_familiar", indicator_id: "despesa_familiar", level: "uf", unit: "Reais",
    row_fields: [{ id: "territorio", label: "Território" }, { id: "c339", label: "Renda" }],
    col_fields: [{ id: "periodo", label: "Período" }, { id: "c12190", label: "Consumo" }],
    rows: incomes.map((id, i) => ({ keys: ["uf:25", id], labels: ["Paraíba", i ? `Renda ${i}` : "Total"] })),
    columns: expenses.map((id, i) => ({ keys: ["2018", id], labels: ["2018", ["Total", "Alimentação", "Habitação", "Vestuário"][i]!] })),
    cells: [[999, 120, 360, 120], [250, 45, 90, 15], [700, 42, 84, 294], [50, 6, 18, 6]]
      .map((row) => row.map((value) => ({ value, status: "valid" }))),
    share_bases: incomes.map((id, i) => ({
      classification_id: "c12190", row_keys: ["uf:25", id], column_keys: ["2018", totals.c12190],
      value: [600, 150, 420, 30][i]!, status: "valid",
    })),
    footer_cells: [],
    provenance: { release_id: "teste", tables: [], derived: false, truncated: false },
  };
}

function show(data: Pivot) {
  return render(<NextIntlClientProvider locale="pt-BR" messages={messages}>
    <PivotTable data={data} totals={totals} shares={false} sharePolicies={policies}
      dimensionOrder={["c339", "c12190"]} selected={null} onSelect={vi.fn()} />
  </NextIntlClientProvider>);
}

describe("percentuais hierárquicos da tabela", () => {
  it("mostra N1 global e N2 sobre o subtotal publicado de cada grupo", () => {
    show(fixture());
    expect(screen.getByText("250").closest("td")?.textContent).toContain("25,0%");
    expect(screen.getByText("45").closest("td")?.textContent).toContain("30,0%");
    expect(screen.getByText("90").closest("td")?.textContent).toContain("60,0%");
    expect(screen.getByText("15").closest("td")?.textContent).toContain("10,0%");
    expect(screen.getByText("999").closest("td")?.textContent).toContain("Base exibida: 1.000");
    expect(screen.getByText(/Composição calculada pelo portal/)).toBeTruthy();
  });

  it("preserva a hierarquia quando renda e despesas mudam de eixo", () => {
    const original = fixture();
    const data = {
      ...original, row_fields: original.col_fields, col_fields: original.row_fields,
      rows: original.columns, columns: original.rows,
      cells: original.columns.map((_, i) => original.rows.map((_, j) => original.cells[j]![i]!)),
      share_bases: original.share_bases!.map((base) => ({ ...base, row_keys: base.column_keys, column_keys: base.row_keys })),
    };
    show(data);
    expect(screen.getByText("250").closest("td")?.textContent).toContain("25,0%");
    expect(screen.getByText("45").closest("td")?.textContent).toContain("30,0%");
    expect(percentageDimension(["periodo", "c12190"], ["territorio", "c339"],
      ["2018", expenses[1]!], ["uf:25", incomes[1]!], totals, ["c339", "c12190"])).toBe("c12190");
  });

  it("não usa soma dos filhos quando o subtotal oficial está ausente", () => {
    show({ ...fixture(), share_bases: [] });
    expect(screen.getByText("45").closest("td")?.textContent).not.toContain("%");
    expect(screen.getByText("250").closest("td")?.textContent).toContain("25,0%");
  });

  it("não duplica o Total e bloqueia a composição quando há sigilo", () => {
    const data = fixture();
    const base = compositionBases(data, totals, policies).get("c339")!;
    expect([...base.values()]).toContain(1000);
    data.cells[1]![0] = { value: null, status: "suppressed" };
    expect([...compositionBases(data, totals, policies).get("c339")!.values()]).toContain(null);
  });
});
