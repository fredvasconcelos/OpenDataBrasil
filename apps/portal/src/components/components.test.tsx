import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import type { Detail, DetailNode, GeoCollection, Kpi, Table } from "../lib/types";
import { DataTable } from "./DataTable";
import { DetailTooltip } from "./DetailTooltip";
import { KpiInfo } from "./KpiInfo";
import { MapView } from "./MapView";

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

describe("MapView", () => {
  // jsdom não tem ResizeObserver: o mapa usa o tamanho inicial.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
  const square = (x: number, y: number) => ({
    type: "Polygon" as const,
    coordinates: [[[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]],
  });
  const collection: GeoCollection = {
    type: "FeatureCollection",
    metadata: { release_id: "r", level: "regiao", within: null },
    features: [
      { type: "Feature", id: "regiao:1", properties: { name: "Norte", uf: null }, geometry: square(-60, -5) },
      { type: "Feature", id: "regiao:2", properties: { name: "Nordeste", uf: null }, geometry: square(-40, -8) },
    ],
  };

  it("desenha os territórios sem dica nativa do navegador e com controles de zoom", () => {
    const onSelect = vi.fn();
    const { container } = wrap(
      <MapView
        collection={collection}
        context={null}
        values={[
          { geography_key: "regiao:1", name: "Norte", value: 10, status: "valid" },
          { geography_key: "regiao:2", name: "Nordeste", value: 20, status: "valid" },
        ]}
        selected={null}
        focus={null}
        canUp={false}
        onHover={vi.fn()}
        onSelect={onSelect}
        onDrill={() => true}
        onUp={vi.fn()}
        onReset={vi.fn()}
        legendTitle="População"
        label="População · Grande Região · 2022"
      />,
    );
    expect(container.querySelectorAll("path.territory")).toHaveLength(2);
    // O <title> do SVG gerava o balão preto ao parar o ponteiro sobre o mapa.
    expect(container.querySelector("title")).toBeNull();
    expect(screen.getByRole("img", { name: /População/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Aproximar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ver o Brasil inteiro" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^Nordeste:/ }));
    expect(onSelect).toHaveBeenCalledWith("regiao:2");
  });
});

describe("MapView com recorte", () => {
  const square = (x: number, y: number) => ({
    type: "Polygon" as const,
    coordinates: [[[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]],
  });
  it("colore só o recorte; o resto do país fica em cinza, com contorno do recorte", () => {
    const regions: GeoCollection = {
      type: "FeatureCollection",
      metadata: { release_id: "r", level: "regiao", within: null },
      features: [
        { type: "Feature", id: "regiao:1", properties: { name: "Norte", uf: null }, geometry: square(-60, -5) },
        { type: "Feature", id: "regiao:2", properties: { name: "Nordeste", uf: null }, geometry: square(-40, -8) },
      ],
    };
    const ufs: GeoCollection = {
      type: "FeatureCollection",
      metadata: { release_id: "r", level: "uf", within: "regiao:1" },
      features: [{ type: "Feature", id: "uf:13", properties: { name: "Amazonas", uf: "AM" }, geometry: square(-60, -5) }],
    };
    const onDrill = vi.fn(() => true);
    const { container } = wrap(
      <MapView
        collection={ufs}
        context={regions}
        values={[{ geography_key: "uf:13", name: "Amazonas", value: 4, status: "valid" }]}
        selected={null}
        focus="regiao:1"
        canUp
        onHover={vi.fn()}
        onSelect={vi.fn()}
        onDrill={onDrill}
        onUp={vi.fn()}
        onReset={vi.fn()}
        legendTitle="População"
        label="Mapa"
      />,
    );
    // Dentro do recorte: a UF colorida. Fora: só o Nordeste, em cinza (o Norte é o recorte).
    expect(screen.getByRole("button", { name: /^Amazonas:/ })).toBeTruthy();
    const outside = container.querySelectorAll("path.territory.context");
    expect(Array.from(outside).map((p) => p.getAttribute("data-key"))).toEqual(["regiao:2"]);
    expect(container.querySelector("path.focus-outline")).toBeTruthy();
    expect(screen.getByText("Fora do recorte")).toBeTruthy();
    // Duplo clique num território de fora abre o recorte nele.
    fireEvent.doubleClick(outside[0] as Element);
    expect(onDrill).toHaveBeenCalledWith("regiao:2", "click");
  });
});

describe("KpiInfo", () => {
  // jsdom não tem matchMedia: simula a janela estreita (< 1600 px), com o bloco aberto.
  globalThis.matchMedia ??= ((query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })) as unknown as typeof matchMedia;

  it("mostra a linha da fonte e o bloco recolhível com descrição e limitações", () => {
    const kpi = {
      kpi_id: "k",
      label: "População",
      description: "Pessoas residentes.",
      unit: "Pessoas",
      periods: ["2010", "2022"],
      caveats: ["Nota A"],
      source: { dataset_id: "d", source_table_id: "9606", source_variable_id: "93", source_variable_name: null, reference_url: null, license_id: "ibge" },
    } as unknown as Kpi;
    const { container } = wrap(<KpiInfo kpi={kpi} releaseId="81f68da1-6c5f-4686-9ea9-6818a24b8db4" />);
    const source = container.querySelector(".meta-source");
    expect(source?.textContent).toContain("Tabela SIDRA 9606, variável 93");
    expect(source?.textContent).toContain("81f68da1");
    const more = container.querySelector("details.meta-more") as HTMLDetailsElement;
    expect(more.open).toBe(true);
    expect(more.textContent).toContain("Pessoas residentes.");
    expect(more.textContent).toContain("Nota A");
    expect(more.textContent).toContain("2010–2022");
  });
});
