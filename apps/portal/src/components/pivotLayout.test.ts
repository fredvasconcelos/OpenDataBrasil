import { describe, expect, it } from "vitest";

import { columnGroups, visibleColumnLevels } from "@/components/PivotTable";

// DS 2.17: cabeçalho da tabela dinâmica sem a linha de período único e com grupos mesclados.
const col = (keys: string[], labels: string[]) => ({ keys, labels });
const fields = [{ id: "periodo", label: "Período" }, { id: "c86", label: "Cor ou raça" }, { id: "c2", label: "Sexo" }];
const one = [
  col(["2022", "c86:t", "c2:t"], ["2022", "Total", "Total"]),
  col(["2022", "c86:t", "c2:4"], ["2022", "Total", "Homens"]),
  col(["2022", "c86:1", "c2:t"], ["2022", "Branca", "Total"]),
  col(["2022", "c86:1", "c2:4"], ["2022", "Branca", "Homens"]),
];

describe("visibleColumnLevels", () => {
  it("omite o Período quando há um só valor (ele já está no título)", () => {
    expect(visibleColumnLevels({ col_fields: fields, columns: one })).toEqual([1, 2]);
  });
  it("mantém o Período com mais de um valor", () => {
    const two = [...one, col(["2010", "c86:t", "c2:t"], ["2010", "Total", "Total"])];
    expect(visibleColumnLevels({ col_fields: fields, columns: two })).toEqual([0, 1, 2]);
  });
  it("mantém o último nível mesmo sendo o Período (é o da ordenação)", () => {
    expect(visibleColumnLevels({ col_fields: [fields[0]!], columns: [col(["2022"], ["2022"])] })).toEqual([0]);
  });
  it("não omite outro campo de valor único (um filtro de categoria não está no título)", () => {
    const sexo = [col(["c2:4", "c86:t"], ["Homens", "Total"]), col(["c2:4", "c86:1"], ["Homens", "Branca"])];
    expect(visibleColumnLevels({ col_fields: [fields[2]!, fields[1]!], columns: sexo })).toEqual([0, 1]);
  });
});

describe("columnGroups", () => {
  it("agrupa colunas seguidas com o mesmo grupo em todos os níveis de cima", () => {
    expect(columnGroups(one, 1)).toEqual([
      { start: 0, span: 2, label: "Total" },
      { start: 2, span: 2, label: "Branca" },
    ]);
  });
  it("quebra o grupo quando o nível de cima muda, mesmo com o mesmo rótulo", () => {
    const anos = [
      col(["2010", "c86:t"], ["2010", "Total"]),
      col(["2022", "c86:t"], ["2022", "Total"]),
    ];
    expect(columnGroups(anos, 1)).toHaveLength(2);
  });
});
