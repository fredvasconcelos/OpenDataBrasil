import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import type { Detail, DetailNode, Table } from "../lib/types";
import { DataTable } from "./DataTable";
import { DetailTooltip } from "./DetailTooltip";

afterEach(cleanup);

const wrap = (ui: React.ReactNode) =>
  render(
    <NextIntlClientProvider locale="pt-BR" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  );

const node = (label: string, value: number | null, share: number | null, children: DetailNode[] = [], status = "valid"): DetailNode => ({
  label,
  classification_id: null,
  category_key: label,
  value,
  status: value === null ? status : "valid",
  share_pct: share,
  children,
});

const base = (root: DetailNode): Detail => ({
  kpi_id: "populacao_residente",
  indicator_id: "censo_populacao_cor_raca_sexo",
  geography: { geography_key: "uf:29", name: "Bahia", level_id: "uf" },
  period: "2022",
  unit: "Pessoas",
  additivity: "additive",
  dimensions: ["c86", "c2"],
  notes: [],
  provenance: { release_id: "r", tables: [], derived: false, truncated: false },
  root,
});

// Cor ou raça > sexo, com um valor sob sigilo.
const detail = base(
  node("Total", 14141626, null, [
    node("Parda", 8103964, 57.31, [node("Homens", 3911184, 48.26), node("Mulheres", null, null, [], "suppressed")]),
  ]),
);

describe("DetailTooltip", () => {
  it("mostra o território, o total, as categorias e a divisão por sexo", () => {
    wrap(<DetailTooltip name="Bahia" detail={detail} loading={false} x={10} y={10} />);
    const tip = screen.getByRole("tooltip");
    expect(within(tip).getByText("Bahia")).toBeTruthy();
    expect(within(tip).getByText("2022")).toBeTruthy();
    expect(within(tip).getByText("14.141.626")).toBeTruthy();
    expect(within(tip).getByText("Parda")).toBeTruthy();
    expect(within(tip).getByText("8.103.964")).toBeTruthy();
    expect(tip.textContent).toContain("57,3%");
    expect(tip.textContent).toContain("Homens");
    expect(tip.textContent).toContain("48,3%");
    expect(tip.textContent).toContain("X (sigilo)");
    expect(tip.textContent).toContain("Percentuais calculados pela plataforma");
  });

  it("ordena as categorias do maior para o menor valor", () => {
    const d = base(node("Total", 100, null, [node("Branca", 20, 20), node("Parda", 70, 70), node("Preta", 10, 10)]));
    wrap(<DetailTooltip name="Bahia" detail={d} loading={false} x={10} y={10} />);
    const labels = Array.from(screen.getByRole("tooltip").querySelectorAll(".tt-label")).map((el) => el.textContent);
    expect(labels).toEqual(["Parda", "Branca", "Preta"]);
  });

  it("usa o pictograma quando só sexo está marcado", () => {
    const d = base(node("Total", 1000, null, [node("Homens", 499, 49.9), node("Mulheres", 501, 50.1)]));
    wrap(<DetailTooltip name="Alcântara" detail={d} loading={false} x={10} y={10} />);
    const tip = screen.getByRole("tooltip");
    expect(within(tip).getByRole("img").getAttribute("aria-label")).toBe("Homens 49,9%, Mulheres 50,1%");
    expect(tip.textContent).toContain("Cada figura");
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
