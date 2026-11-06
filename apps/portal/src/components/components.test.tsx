import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import type { Detail, Table } from "../lib/types";
import { DataTable } from "./DataTable";
import { DetailTooltip } from "./DetailTooltip";

afterEach(cleanup);

const wrap = (ui: React.ReactNode) =>
  render(
    <NextIntlClientProvider locale="pt-BR" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  );

const detail: Detail = {
  kpi_id: "populacao_residente",
  indicator_id: "censo_populacao_cor_raca_sexo",
  geography: { geography_key: "uf:29", name: "Bahia", level_id: "uf" },
  period: "2022",
  unit: "Pessoas",
  additivity: "additive",
  dimensions: ["c86", "c2"],
  notes: [],
  provenance: { release_id: "r", tables: [], derived: false, truncated: false },
  root: {
    label: "Total",
    classification_id: null,
    category_key: null,
    value: 14141626,
    status: "valid",
    share_pct: null,
    children: [
      {
        label: "Parda",
        classification_id: "c86",
        category_key: "c86:2779",
        value: 8103964,
        status: "valid",
        share_pct: 57.31,
        children: [
          { label: "Homens", classification_id: "c2", category_key: "c2:4", value: 3911184, status: "valid", share_pct: 48.26, children: [] },
          { label: "Mulheres", classification_id: "c2", category_key: "c2:5", value: null, status: "suppressed", share_pct: null, children: [] },
        ],
      },
    ],
  },
};

describe("DetailTooltip", () => {
  it("mostra só o território, com sub-KPIs aninhados e percentuais", () => {
    wrap(<DetailTooltip name="Bahia" detail={detail} loading={false} x={10} y={10} />);
    const tip = screen.getByRole("tooltip");
    expect(within(tip).getByText("Bahia")).toBeTruthy();
    const rows = within(tip).getAllByRole("row").map((r) => r.textContent);
    expect(rows).toEqual(["Total14.141.626", "Parda8.103.96457,3%", "Homens3.911.18448,3%", "MulheresX (sigilo)"]);
    expect(tip.textContent).toContain("Percentuais calculados pela plataforma");
  });

  it("mostra carregando enquanto o detalhe não chega", () => {
    wrap(<DetailTooltip name="Acre" detail={null} loading x={0} y={0} />);
    expect(screen.getByRole("tooltip").textContent).toContain("Carregando");
  });
});

describe("DataTable", () => {
  const table: Table = {
    kpi_id: "k",
    indicator_id: "i",
    level: "uf",
    period: "2022",
    unit: "Pessoas",
    columns: [
      { key: "c2:6794", label: "Total", depth: 0 },
      { key: "c2:4", label: "Homens", depth: 1 },
    ],
    rows: [
      { geography_key: "uf:29", name: "Bahia", uf_abbreviation: "BA", cells: { "c2:6794": { value: 10, status: "valid" } } },
      { geography_key: "uf:21", name: "Maranhão", uf_abbreviation: "MA", cells: { "c2:6794": { value: 5, status: "valid" }, "c2:4": { value: 2, status: "valid" } } },
    ],
    total_rows: 27,
    offset: 0,
    limit: 2,
    provenance: { release_id: "r", tables: [], derived: false, truncated: false },
  };

  it("pagina, ordena e seleciona territórios", () => {
    const onPage = vi.fn();
    const onSort = vi.fn();
    const onSelect = vi.fn();
    wrap(<DataTable data={table} selected="uf:29" sort="value" order="desc" onSort={onSort} onPage={onPage} onSelect={onSelect} />);
    expect(screen.getByText("1–2 de 27")).toBeTruthy();
    expect(screen.getByText("sem dado")).toBeTruthy();
    fireEvent.click(screen.getByText("Maranhão"));
    expect(onSelect).toHaveBeenCalledWith("uf:21");
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    expect(onPage).toHaveBeenCalledWith(2);
    expect((screen.getByRole("button", { name: "Anterior" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Ordenar por nome" }));
    expect(onSort).toHaveBeenCalledWith("name");
  });
});
