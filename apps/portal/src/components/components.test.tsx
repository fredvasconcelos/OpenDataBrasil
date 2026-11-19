import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import type { Detail, DetailNode, GeoCollection, Kpi, Navigation, Pivot, Series } from "../lib/types";
import { DetailTooltip, groupedLayout, groupedRows, tooltipMode } from "./DetailTooltip";
import { navFixture } from "../lib/fixtures";
import { allKpis } from "../lib/state";
import { AboutCatalog } from "./AboutCatalog";
import { HomeCatalog } from "./HomeCatalog";
import { KpiInfo } from "./KpiInfo";
import { MapView } from "./MapView";
import { ProjectLinks } from "./ProjectLinks";
import { SeriesChart } from "./SeriesChart";
import { SupportOptions } from "./SupportOptions";
import { Sidebar } from "./Sidebar";

afterEach(cleanup);

const wrap = (ui: React.ReactNode) =>
  render(
    <NextIntlClientProvider locale="pt-BR" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  );

const node = (label: string, value: number | null, share: number | null, children: DetailNode[] = [], status = "valid"): DetailNode => ({
  label,
  full_label: label,
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

it("preserva os percentuais de cada grupo nas células da matriz do tooltip", () => {
  const children = (value: number) => Array.from({ length: 8 }, (_, i) =>
    node(`Categoria ${i + 1}`, value / 8, 12.5),
  );
  const grouped = base(node("Total", 200, 100, [
    node("Grupo A", 50, 25, children(50)),
    node("Grupo B", 150, 75, children(150)),
  ]));
  wrap(<DetailTooltip name="Bahia" detail={grouped} loading={false} x={100} y={100} />);
  const table = screen.getByRole("table");
  expect(within(table).getAllByText("(12,5%)")).toHaveLength(16);
  expect(screen.getByText("(100,0%)")).toBeTruthy();
  expect(within(screen.getByRole("tooltip")).getByText("25,0%")).toBeTruthy();
  expect(within(screen.getByRole("tooltip")).getByText("75,0%")).toBeTruthy();
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

  it("abre a forma matriz (larga e baixa) quando as categorias têm os mesmos filhos", () => {
    const groups = ["2.1.1 Alimentação", "2.1.2 Habitação", "2.1.3 Vestuário", "2.1.4 Transporte"];
    const cls = (label: string, value: number) =>
      node(label, value, null, groups.map((g, i) => node(g, value / (i + 2), null)));
    const d = {
      ...base(node("Total", 3166.07, null, [cls("Até 1.908 Reais", 1500), cls("Mais de 23.850 Reais", 24303.39), cls("Mais de 9.540 a 14.310 Reais", 9389.06), cls("Mais de 2.862 a 5.724 Reais", 3583.07)])),
      unit: "Reais",
      additivity: "non_additive",
    };
    wrap(<DetailTooltip name="Nordeste" detail={d} loading={false} x={10} y={10} />);
    const tip = screen.getByRole("tooltip");
    expect(tip.className).toContain("matrix");
    const labels = Array.from(tip.querySelectorAll(".tt-summary .tt-label")).map((el) => el.textContent);
    expect(labels[0]).toBe("Mais de 23.850 Reais");
    const rows = Array.from(tip.querySelectorAll(".tt-grid tbody th")).map((el) => el.textContent);
    expect(rows).toEqual(["2.1.1Alimentação", "2.1.2Habitação", "2.1.3Vestuário", "2.1.4Transporte"]);
    expect(tip.querySelectorAll(".tt-grid tbody td")).toHaveLength(16);
    expect(tip.textContent).toContain("proporcionais ao maior valor");
  });

  it("mantém a forma normal para cor ou raça › sexo", () => {
    wrap(<DetailTooltip name="Bahia" detail={detail} loading={false} x={10} y={10} />);
    expect(screen.getByRole("tooltip").className).toBe("tooltip");
  });

  it("mostra carregando enquanto o detalhe não chega", () => {
    wrap(<DetailTooltip name="Acre" detail={null} loading x={0} y={0} />);
    expect(screen.getByRole("tooltip").textContent).toContain("Carregando");
  });
});

describe("SeriesChart", () => {
  class RO {
    observe() {}
    disconnect() {}
  }
  vi.stubGlobal("ResizeObserver", RO);
  const pts = (years: number[]) => years.map((y, i) => ({ period: String(y), value: 1000 + i * 10, status: "valid" }));
  const series = (years: number[]): Series =>
    ({
      kpi_id: "k",
      indicator_id: "i",
      geography: { geography_key: "pais:1", name: "Brasil", level_id: "brasil" },
      unit: "Pessoas",
      series: [{ key: "total", label: "Brasil", categories: {}, points: pts(years) }],
      provenance: { release_id: "r", tables: [], derived: false, truncated: false },
    }) as unknown as Series;

  it("liga anos não publicados com traço pontilhado e avisa na legenda", () => {
    const { container } = wrap(<SeriesChart data={series([2001, 2002, 2003, 2005, 2006])} />);
    expect(container.querySelectorAll(".series-gap")).toHaveLength(1);
    expect(container.textContent).toContain("Períodos sem publicação");
  });

  it("mostra o tooltip do período sob o ponteiro e navega pelo teclado", () => {
    const { container } = wrap(<SeriesChart data={series([2019, 2020, 2021])} />);
    const svg = container.querySelector("svg") as SVGSVGElement;
    expect(container.querySelector("title")).toBeNull();
    fireEvent.keyDown(svg, { key: "End" });
    expect(screen.getByRole("tooltip").textContent).toContain("2021");
    expect(screen.getByRole("tooltip").textContent).toContain("1.020");
    fireEvent.keyDown(svg, { key: "ArrowLeft" });
    expect(screen.getByRole("tooltip").textContent).toContain("2020");
    fireEvent.keyDown(svg, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("marca a mudança de fonte numa série composta (ADR-0022)", () => {
    const data = {
      ...series([2010, 2016, 2017]),
      series: [
        {
          key: "total",
          label: "Brasil",
          categories: {},
          points: [
            { period: "2010", value: 90.4, status: "valid", source_table_id: "9841" },
            { period: "2016", value: 92.8, status: "valid", source_table_id: "7113" },
            { period: "2017", value: 93.0, status: "valid", source_table_id: "7113" },
          ],
        },
      ],
    } as unknown as Series;
    const { container } = wrap(<SeriesChart data={data} />);
    expect(container.querySelectorAll(".series-source-change")).toHaveLength(1);
    expect(container.querySelector(".series-legend")?.textContent).toContain("Mudança de fonte");
    fireEvent.keyDown(container.querySelector("svg") as SVGSVGElement, { key: "Home" });
    expect(screen.getByRole("tooltip").textContent).toContain("Fonte do ponto: tabela 9841");
  });

  it("série de uma fonte só não marca mudança", () => {
    const { container } = wrap(<SeriesChart data={series([2019, 2020, 2021])} />);
    expect(container.querySelector(".series-source-change")).toBeNull();
  });

  it("com detalhe, tira o Total das linhas, da legenda e do eixo Y, mas mantém no tooltip", () => {
    const cat = (key: string, label: string, v: number) => ({
      key,
      label,
      categories: { c86: key },
      depth: 1,
      points: [2019, 2020].map((y) => ({ period: String(y), value: v, status: "valid" })),
    });
    const data = {
      ...series([2019, 2020]),
      series: [
        { key: "c86:0", label: "Total", categories: { c86: "c86:0" }, depth: 0, points: [2019, 2020].map((y) => ({ period: String(y), value: 900_000, status: "valid" })) },
        cat("2776", "Branca", 400),
        cat("2777", "Preta", 120),
      ],
    } as unknown as Series;
    const { container } = wrap(<SeriesChart data={data} additive />);
    const legend = container.querySelector(".series-legend")?.textContent ?? "";
    expect(legend).toContain("Branca");
    expect(legend).not.toContain("Total");
    // Eixo Y na escala das categorias (centenas), não do Total (900 mil).
    const yLabels = [...container.querySelectorAll("svg text")].map((t) => t.textContent ?? "");
    expect(yLabels.some((l) => /mil/.test(l))).toBe(false);
    expect(container.querySelectorAll("svg path[fill='none']")).toHaveLength(2);
    fireEvent.keyDown(container.querySelector("svg") as SVGSVGElement, { key: "End" });
    const tip = screen.getByRole("tooltip");
    expect(tip.querySelector(".series-tip-total")?.textContent).toContain("Total");
    expect(tip.textContent).toContain("900.000");
    // % do Total do período nas categorias (KPI aditivo): Branca 400 de 900.000.
    expect(tip.textContent).toContain("400 (0,0%)");
    expect(tip.querySelector(".series-tip-total .share")).toBeNull();
  });
});

describe("percentuais recebidos na série", () => {
  it("usa a base do grupo enviada pela API e mantém o Total oficial separado", () => {
    const data: Series = {
      kpi_id: "despesa_familiar", indicator_id: "despesa_familiar", unit: "Reais",
      geography: { geography_key: "uf:25", name: "Paraíba", level_id: "uf" },
      share_methods: ["published_group"],
      series: [
        { key: "total", label: "Total", full_label: "Total", categories: {}, depth: 0,
          points: [{ period: "2018", value: 999, status: "valid", share_pct: null, share_base_value: 600 }] },
        { key: "c12190:103539", label: "Alimentação", full_label: "Alimentação", categories: { c12190: "c12190:103539" }, depth: 1,
          points: [{ period: "2018", value: 120, status: "valid", share_pct: 20, share_base_value: 600 }] },
      ],
      provenance: { release_id: "teste", tables: [], derived: false, truncated: false },
    };
    const { container } = wrap(<SeriesChart data={data} />);
    fireEvent.keyDown(container.querySelector("svg") as SVGSVGElement, { key: "End" });
    const tip = screen.getByRole("tooltip");
    expect(tip.textContent).toContain("120 (20,0%)");
    expect(tip.textContent).toContain("Base do grupo: 600 (100,0%)");
    expect(tip.querySelector(".series-tip-total")?.textContent).toContain("999");
    expect(tip.querySelector(".series-tip-total .share")).toBeNull();
  });
});

describe("SeasonChart (Isolar período)", () => {
  it("uma barra por ano marcado em cada parte, sem somar entre anos (ADR-0026)", async () => {
    const { seasonBars, partOf } = await import("./SeasonChart");
    expect(partOf("2025M08")).toBe("M08");
    expect(partOf("2025T3")).toBe("T3");
    const data = {
      kpi_id: "k",
      indicator_id: "i",
      geography: { geography_key: "brasil:1", name: "Brasil", level_id: "brasil" },
      unit: "Vítimas",
      series: [
        {
          key: "total",
          label: "Total",
          full_label: "Total",
          categories: {},
          depth: 0,
          points: [
            { period: "2024M01", value: 100, status: "valid" },
            { period: "2024M02", value: 90, status: "valid" },
            { period: "2025M01", value: 110, status: "valid" },
            { period: "2025M02", value: null, status: "absent" },
          ],
        },
      ],
      provenance: { release_id: "r", tables: [], derived: false, truncated: false },
    } as unknown as Series;
    const { bars, labels, years } = seasonBars(data);
    expect(years).toEqual(["2024", "2025"]);
    expect(labels).toEqual(["2024", "2025"]);
    expect(bars.map((b) => [b.part, ...b.values])).toEqual([
      ["M01", 100, 110],
      ["M02", 90, null],
    ]);
    expect(bars[1]?.statuses[1]).toBe("absent");
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

  it("apresenta o subtotal regional com identificação acessível e nota de parcialidade", () => {
    wrap(
      <MapView
        collection={collection} context={null}
        values={[
          { geography_key: "regiao:1", name: "Norte", value: 10, status: "partial_sum" },
          { geography_key: "regiao:2", name: "Nordeste", value: 20, status: "derived_sum" },
        ]}
        selected={null} focus={null} canUp={false}
        onHover={vi.fn()} onSelect={vi.fn()} onDrill={() => true} onUp={vi.fn()} onReset={vi.fn()}
        legendTitle="Óbitos" label="Óbitos · Grande Região · 2024"
      />,
    );
    expect(screen.getByRole("button", { name: "Norte: 10 (parcial)" })).toBeTruthy();
    expect(screen.getByRole("note").textContent).toContain("Valores parciais");
    expect(screen.getByRole("button", { name: "Nordeste: 20" })).toBeTruthy();
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

describe("HomeCatalog", () => {
  it("mostra a grade de temas, filtra por etiqueta e busca pelo número da tabela", () => {
    wrap(<HomeCatalog nav={navFixture} releaseId="r1" />);
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toContain("População e demografia");
    fireEvent.click(screen.getByRole("button", { name: /Saúde/ }));
    expect(screen.getByRole("button", { name: /Saúde/ }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.queryByText("População estimada")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Todos/ }));
    fireEvent.change(screen.getByLabelText("Buscar indicador"), { target: { value: "9606" } });
    expect(screen.getByText("População residente (Censo)")).toBeTruthy();
    expect(screen.queryByText("População estimada")).toBeNull();
    expect(screen.getByText("1 indicador encontrado")).toBeTruthy();
  });

  it("abre a prévia com os metadados e fecha com Esc", () => {
    wrap(<HomeCatalog nav={navFixture} releaseId="r1" />);
    fireEvent.click(screen.getByRole("button", { name: "População estimada" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("2001–2026 (3)")).toBeTruthy();
    expect(within(dialog).getByText("ibge-reuso-com-citacao")).toBeTruthy();
    expect(within(dialog).getByText("Limitação de teste.")).toBeTruthy();
    expect(within(dialog).getByRole("link", { name: "Abrir no painel" }).getAttribute("href")).toBe("/dashboard?kpi=populacao_estimada");
    expect(document.activeElement?.getAttribute("aria-label")).toBe("Fechar");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("AboutCatalog", () => {
  it("lista por tema e abre a linha com todos os metadados", () => {
    wrap(<AboutCatalog nav={navFixture} releaseId="81f68da1-6c5f" activated={null} licenseReview="algumas em revisão" />);
    expect(screen.getByText("Licenças: algumas em revisão")).toBeTruthy();
    const row = screen.getByRole("button", { name: /População residente \(Censo\)/ });
    expect(row.textContent).toContain("9606");
    expect(row.textContent).toContain("Cor ou raça");
    fireEvent.click(row);
    expect(row.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("link", { name: "Abrir no painel" })).toBeTruthy();
  });
});

describe("Sidebar · busca", () => {
  const props = {
    nav: navFixture,
    kpi: null,
    dimensions: [],
    onKpi: vi.fn(),
    onDimensions: vi.fn(),
    level: "uf",
    selection: ["2022"],
    grain: null,
    onLevel: vi.fn(),
    onPeriods: vi.fn(),
    onGrain: vi.fn(),
    onClear: vi.fn(),
    canClear: false,
  };

  it("filtra a árvore, marca o termo e mostra o trecho da descrição", () => {
    const { container } = wrap(<Sidebar {...props} />);
    fireEvent.change(screen.getByLabelText("Buscar tema ou indicador"), { target: { value: "fundo de participacao" } });
    expect(screen.getByText("1 indicador em 1 tema")).toBeTruthy();
    expect(container.querySelector(".tree-snippet mark")?.textContent).toBe("Fundo de Participação");
    expect(screen.queryByText("Pessoas com pelo menos uma doença crônica")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Limpar" }));
    expect(screen.getByText("Todos os temas")).toBeTruthy();
  });

  it("mostra o grão de tempo só para KPIs que somam no tempo (ADR-0013)", () => {
    const onGrain = vi.fn();
    const months = ["2025M11", "2025M12"];
    const flow = {
      ...allKpis(navFixture)[0]!,
      periods: months,
      time_grains: [
        { grain: "mes", label: "Mês", periods: months, complete_periods: months },
        { grain: "trimestre", label: "Trimestre", periods: ["2025T4"], complete_periods: [] },
        { grain: "ano", label: "Ano", periods: ["2025"], complete_periods: [] },
      ],
    };
    wrap(<Sidebar {...props} kpi={flow} selection={["2025T4"]} grain="trimestre" onGrain={onGrain} />);
    const group = screen.getByRole("group", { name: "Período por" });
    expect(within(group).getAllByRole("radio").map((r) => (r as HTMLInputElement).checked)).toEqual([false, true, false]);
    // Período recolhido (DS 2.9): o resumo mostra a seleção e abre a árvore.
    const summary = screen.getByRole("button", { name: /T4 2025/ });
    expect(summary.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(summary);
    // Período em árvore (ADR-0026): o ano aberto mostra o trimestre marcado, em andamento.
    const t4 = screen.getByRole("checkbox", { name: /T4 2025/ }) as HTMLInputElement;
    expect(t4.checked).toBe(true);
    expect(t4.closest(".check")?.textContent).toContain("(parcial)");
    fireEvent.click(within(group).getByRole("radio", { name: "Mês" }));
    expect(onGrain).toHaveBeenCalledWith(null);
    // Estoque ou taxa (um grão só): sem o seletor.
    cleanup();
    wrap(<Sidebar {...props} kpi={allKpis(navFixture)[0]!} />);
    expect(screen.queryByRole("group", { name: "Período por" })).toBeNull();
  });

  it("avisa quando não há resultado", () => {
    wrap(<Sidebar {...props} />);
    fireEvent.change(screen.getByLabelText("Buscar tema ou indicador"), { target: { value: "xyzw" } });
    expect(screen.getByText("Nenhum indicador para “xyzw”")).toBeTruthy();
  });
});

describe("ProjectLinks", () => {
  it("no cabeçalho mostra só Instagram e GitHub, em botões com rótulo acessível (Contato vai no menu)", () => {
    const { container } = wrap(
      <ProjectLinks
        variant="header"
        contactUrl="mailto:contato@exemplo.org"
        instagramUrl="https://instagram.com/opendatabrasil"
        repoUrl="https://github.com/org/repo"
      />,
    );
    expect(screen.queryByRole("link", { name: "Contato" })).toBeNull();
    const insta = screen.getByRole("link", { name: "Instagram do projeto" });
    expect(insta.getAttribute("href")).toBe("https://instagram.com/opendatabrasil");
    expect(insta.getAttribute("rel")).toContain("noopener");
    const repo = screen.getByRole("link", { name: "Repositório do projeto no GitHub" });
    expect(repo.getAttribute("target")).toBe("_blank");
    expect(repo.getAttribute("rel")).toContain("noopener");
    expect(container.querySelector("svg[viewBox='0 0 16 16']")).toBeTruthy();
  });

  it("no rodapé mostra e-mail, Instagram e GitHub como ícones e esconde o que não foi configurado", () => {
    const { container } = wrap(
      <ProjectLinks variant="footer" contactUrl="mailto:contato@exemplo.org" instagramUrl={null} repoUrl="https://github.com/org/repo" />,
    );
    const contact = screen.getByRole("link", { name: "Contato" });
    expect(contact.getAttribute("href")).toBe("mailto:contato@exemplo.org");
    expect(contact.getAttribute("target")).toBeNull();
    expect(screen.getByRole("link", { name: "Repositório do projeto no GitHub" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Instagram/ })).toBeNull();
    expect(container.querySelectorAll("a.footer-icon")).toHaveLength(2);
    expect(screen.queryByText("Contato")).toBeNull();
  });
});

describe("LanguageMenu", () => {
  it("mostra o idioma atual e deixa inglês e espanhol como 'em breve'", async () => {
    const { LanguageMenu } = await import("./LanguageMenu");
    wrap(<LanguageMenu />);
    const button = screen.getByRole("button", { name: "Idioma: Português (Brasil)" });
    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    const list = within(screen.getByRole("list", { name: "Idioma" }));
    expect(list.getByRole("button", { name: /Português/ }).getAttribute("aria-current")).toBe("true");
    expect((list.getByRole("button", { name: /English/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((list.getByRole("button", { name: /Español/ }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
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

  it("fonte fora do SIDRA mostra a instituição e a tabela de origem (ex.: Sinesp)", () => {
    const kpi = {
      kpi_id: "k",
      label: "Homicídios",
      description: "",
      unit: "Vítimas",
      periods: ["2015M01"],
      caveats: [],
      source: {
        dataset_id: "mjsp-sinesp-vde",
        source_table_id: "SINESP-VDE",
        source_variable_id: "homicidio-doloso",
        source_variable_name: null,
        reference_url: null,
        license_id: "mjsp-dados-abertos",
        institution: "MJSP",
        system: null,
      },
    } as unknown as Kpi;
    const { container } = wrap(<KpiInfo kpi={kpi} releaseId="2f89b1f9-1dca" />);
    const source = container.querySelector(".meta-source")?.textContent ?? "";
    expect(source).toContain("MJSP · SINESP-VDE, variável homicidio-doloso");
    expect(source).not.toContain("SIDRA");
  });

  it("tabelas-irmãs: cita as tabelas do detalhe ativo e lista todas em Sobre", () => {
    const kpi = {
      kpi_id: "diabetes",
      label: "Diagnóstico de diabetes",
      description: "",
      unit: "Mil pessoas",
      periods: ["2013", "2019"],
      caveats: [],
      dimensions: [
        { classification_id: "c86", label: "Cor ou raça", source_table_ids: ["4490"], categories: [] },
        { classification_id: "c2", label: "Sexo", source_table_ids: ["4487"], categories: [] },
      ],
      source: {
        dataset_id: "ibge-serie-4487",
        source_table_id: "4487",
        source_variable_id: "4462",
        source_variable_name: null,
        reference_url: "https://sidra.ibge.gov.br/tabela/4487",
        license_id: "ibge",
        institution: "IBGE",
        system: "SIDRA",
        tables: [
          { table_id: "4487", reference_url: "https://sidra.ibge.gov.br/tabela/4487", classification_ids: ["c2"], periods: ["2013", "2019"] },
          { table_id: "4490", reference_url: "https://sidra.ibge.gov.br/tabela/4490", classification_ids: ["c86"], periods: ["2013", "2019"] },
        ],
      },
    } as unknown as Kpi;
    const { container } = wrap(<KpiInfo kpi={kpi} releaseId="r" dimensions={["c86"]} />);
    const source = container.querySelector(".meta-source") as HTMLElement;
    expect(source.textContent).toContain("Tabelas SIDRA 4487 (Total) e 4490 (Cor ou raça), variável 4462");
    expect(within(source).getByRole("link", { name: "4490" }).getAttribute("href")).toBe("https://sidra.ibge.gov.br/tabela/4490");
    cleanup();
    const plain = wrap(<KpiInfo kpi={kpi} releaseId="r" />).container;
    expect(plain.querySelector(".meta-source")?.textContent).toContain("Tabela SIDRA 4487, variável 4462");
    expect(screen.getByRole("button", { name: "2 tabelas de origem" })).toBeTruthy();
    const list = plain.querySelector(".source-tables")?.textContent ?? "";
    expect(list).toContain("Tabela 4487 · Total, Sexo · 2013, 2019");
    expect(list).toContain("Tabela 4490 · Cor ou raça");
  });
});

describe("SeriesChart com períodos da Gold", () => {
  class RO {
    observe() {}
    disconnect() {}
  }
  vi.stubGlobal("ResizeObserver", RO);
  const monthly = {
    kpi_id: "ipca",
    indicator_id: "ipca",
    geography: { geography_key: "brasil:1", name: "Brasil", level_id: "brasil" },
    unit: "%",
    series: [
      {
        key: "total",
        label: "Brasil",
        categories: {},
        points: ["1998M01", "1998M02", "1998M03"].map((period, i) => ({ period, value: 0.5 + i / 10, status: "valid" })),
      },
    ],
    provenance: { release_id: "r", tables: [], derived: false, truncated: false },
  } as unknown as Series;

  it("lê os meses AAAAMmm no eixo de tempo e mostra o mês por extenso", () => {
    const { container } = wrap(<SeriesChart data={monthly} />);
    const svg = container.querySelector("svg") as SVGSVGElement;
    expect(container.textContent).toContain("jan 1998");
    expect(container.querySelectorAll(".series-gap")).toHaveLength(0);
    fireEvent.keyDown(svg, { key: "End" });
    expect(screen.getByRole("tooltip").textContent).toContain("mar 1998");
  });
});

describe("Sidebar", () => {
  const live = { kpi_id: "populacao_estimada", label: "População estimada", levels: [], map_levels: [], periods: [], dimensions: [] } as unknown as Kpi;
  const nav: Navigation = {
    release_id: "r",
    scope: "demografia",
    dimension_order: [],
    themes: [
      {
        theme_id: "populacao",
        label: "População e demografia",
        filters: [{ filter_id: "sexo", label: "Sexo" }],
        subthemes: [
          {
            subtheme_id: "tamanho",
            label: "Tamanho e crescimento",
            kpis: [live],
            planned: [{ kpi_id: "crescimento", label: "Taxa de crescimento", source_table_id: "4709", survey: "Censo Demográfico", filters: [], note: null }],
          },
        ],
      },
      {
        theme_id: "agropecuaria",
        label: "Agropecuária",
        filters: [{ filter_id: "produto", label: "Produto" }],
        subthemes: [
          {
            subtheme_id: "lavouras",
            label: "Lavouras",
            kpis: [],
            planned: [{ kpi_id: "pam", label: "Produção das lavouras", source_table_id: "5457", survey: "PAM", filters: ["produto"], note: null }],
          },
        ],
      },
    ],
  };
  const props = { dimensions: [], onDimensions: vi.fn(), level: "", selection: [], grain: null, onLevel: vi.fn(), onPeriods: vi.fn(), onGrain: vi.fn(), onClear: vi.fn(), canClear: false };

  it("abre só o tema do indicador atual e mostra os planejados sem ação", () => {
    const onKpi = vi.fn();
    const { container } = wrap(<Sidebar nav={nav} kpi={live} onKpi={onKpi} {...props} />);
    const themes = container.querySelectorAll<HTMLDetailsElement>("nav.themes > details");
    expect([...themes].map((d) => d.open)).toEqual([true, false]);
    // Tema sem dados publicados: marcado "em preparação".
    expect(themes[1]?.querySelector("summary")?.textContent).toContain("em preparação");
    const planned = container.querySelector("li.planned") as HTMLElement;
    expect(planned.textContent).toContain("Taxa de crescimento");
    expect(planned.getAttribute("title")).toBe("Em preparação · tabela SIDRA 4709 (Censo Demográfico)");
    expect(planned.querySelector("button")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "População estimada" }));
    expect(onKpi).toHaveBeenCalledWith("populacao_estimada");
  });
});

describe("Indicadores em preparação (panorama) no catálogo", () => {
  it("Início: conta, lista sem ação e acha pela tabela prevista", () => {
    const { container } = wrap(<HomeCatalog nav={navFixture} releaseId="r1" />);
    expect(container.querySelector(".home-stats")?.textContent).toContain("1 em preparação");
    fireEvent.click(screen.getByRole("button", { name: /População e demografia/ }));
    const item = screen.getByText("Indicador de teste em preparação").closest(".kpi-pending") as HTMLElement;
    expect(item.textContent).toContain("em preparação");
    expect(item.getAttribute("title")).toContain("tabela SIDRA 9999");
    expect(within(item).queryByRole("button")).toBeNull();
    fireEvent.change(screen.getByLabelText("Buscar indicador"), { target: { value: "9999" } });
    expect(screen.getByText("Indicador de teste em preparação")).toBeTruthy();
    expect(screen.queryByText("População estimada")).toBeNull();
  });

  it("Sobre: filtro de situação e linha própria com a tabela na fonte", () => {
    wrap(<AboutCatalog nav={navFixture} releaseId="r1" activated={null} licenseReview={null} />);
    const group = screen.getByRole("group", { name: "Situação" });
    fireEvent.click(within(group).getByRole("button", { name: "Em preparação" }));
    expect(screen.queryByText("População estimada")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Indicador de teste em preparação/ }));
    expect(screen.getByRole("link", { name: /9999/ }).getAttribute("href")).toBe("https://sidra.ibge.gov.br/tabela/9999");
    fireEvent.click(within(group).getByRole("button", { name: "Publicados" }));
    expect(screen.queryByText("Indicador de teste em preparação")).toBeNull();
  });

  it("Barra lateral: a busca também encontra itens em preparação, sem ação", () => {
    const { container } = wrap(
      <Sidebar
        nav={navFixture}
        kpi={null}
        dimensions={[]}
        onKpi={vi.fn()}
        onDimensions={vi.fn()}
        level="uf"
        selection={["2022"]}
        grain={null}
        onLevel={vi.fn()}
        onPeriods={vi.fn()}
        onGrain={vi.fn()}
        onClear={vi.fn()}
        canClear={false}
      />,
    );
    fireEvent.change(screen.getByLabelText("Buscar tema ou indicador"), { target: { value: "teste em prep" } });
    expect(container.querySelector(".tree-status")?.textContent).toContain("1 indicador em preparação");
    expect(container.querySelector(".tree-empty")).toBeNull();
    const li = container.querySelector("li.planned") as HTMLElement;
    expect(li.querySelector("mark")?.textContent?.toLowerCase()).toBe("teste em prep");
    expect(li.querySelector("button")).toBeNull();
  });
});

describe("tooltip agrupado (DS 2.3.16): checagem automática de altura", () => {
  const groups = (n: number, kids: number) =>
    Array.from({ length: n }, (_, g) =>
      node(`Grupo ${g}`, 100, 10, Array.from({ length: kids }, (_, k) => node(`Produto ${g}.${k}`, 10, 10))),
    );

  it("muitos grupos com produtos diferentes viram colunas largas e baixas", () => {
    const kids = groups(9, 9); // 90 linhas, como grupo de lavoura → produto
    expect(tooltipMode(kids)).toBe("grouped");
    expect(groupedLayout(kids, 1500)).toEqual({ columns: 3, width: 936 });
    expect(groupedLayout(kids, 700).columns).toBe(2); // janela estreita: menos colunas
    expect(groupedLayout(kids, 400).width).toBeLessThanOrEqual(400 - 24);
  });

  it("filhos com zero ou sem dado contam como uma linha só", () => {
    const kids = [node("Frutas", 100, 50, [node("Banana", 60, 60), node("Maçã", 0, 0), node("Marmelo", null, null)])];
    expect(groupedRows(kids)).toBe(3); // categoria + Banana + resumo
  });

  it("poucas linhas ficam na forma normal; filhos iguais seguem a matriz", () => {
    expect(tooltipMode(groups(3, 3))).toBe("normal");
    const same = Array.from({ length: 5 }, (_, g) =>
      node(`Classe ${g}`, 100, 20, ["A", "B", "C", "D"].map((l) => node(l, 25, 25))),
    );
    expect(tooltipMode(same)).toBe("matrix");
  });
});

describe("SupportOptions", () => {
  const none = { apoiase: null, coffee: null, pix: null };

  it("avisa que as contas estão em preparação quando nada foi configurado", () => {
    wrap(<SupportOptions links={none} />);
    expect(screen.getByText(/As contas de doação estão sendo criadas/)).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("mostra só os cartões configurados, com links externos seguros", () => {
    wrap(<SupportOptions links={{ ...none, apoiase: "https://apoia.se/exemplo" }} />);
    const link = screen.getByRole("link", { name: /Apoiar no Apoia.se/ });
    expect(link.getAttribute("href")).toBe("https://apoia.se/exemplo");
    expect(link.getAttribute("rel")).toContain("noopener");
    // DS 2.11: logo oficial no lugar do ícone; o nome fica no alt, que titula o cartão.
    const logo = screen.getByRole("img", { name: "Apoia.se" });
    expect(logo.getAttribute("src")).toBe("/apoie/apoiase-logo.png");
    expect(screen.getByRole("heading", { name: "Apoia.se" })).toBeTruthy();
    expect(screen.queryByText("Buy Me a Coffee")).toBeNull();
    expect(screen.queryByText("PIX")).toBeNull();
  });

  it("mostra os QR Codes configurados e copia o PIX copia e cola (DS 2.9)", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    wrap(
      <SupportOptions
        links={{
          ...none,
          pix: "chave-aleatoria",
          pixCode: "000201-exemplo",
          pixQr: "/apoie/pix-qr.svg",
          coffee: "https://buymeacoffee.com/exemplo",
          coffeeQr: "/apoie/bmac-qr.png",
        }}
      />,
    );
    expect(screen.getByRole("img", { name: /QR Code PIX/ }).getAttribute("src")).toBe("/apoie/pix-qr.svg");
    expect(screen.getByRole("img", { name: /Buy Me a Coffee/ }).getAttribute("src")).toBe("/apoie/bmac-qr.png");
    fireEvent.click(screen.getByRole("button", { name: "Copiar PIX copia e cola" }));
    expect(await screen.findByText(/Código copia e cola copiado/)).toBeTruthy();
    expect(writeText).toHaveBeenCalledWith("000201-exemplo");
  });

  it("sem QR nem copia e cola configurados, o cartão PIX mostra só a chave", () => {
    wrap(<SupportOptions links={{ ...none, pix: "chave" }} />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("button", { name: "Copiar PIX copia e cola" })).toBeNull();
  });

  it("copia a chave PIX e anuncia o resultado", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    wrap(<SupportOptions links={{ ...none, pix: "pix@exemplo.org" }} />);
    expect(screen.getByText("pix@exemplo.org")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Copiar chave PIX" }));
    expect(await screen.findByText("Chave copiada.")).toBeTruthy();
    expect(writeText).toHaveBeenCalledWith("pix@exemplo.org");
  });

  it("posiciona a transferência após o PIX e copia agência, operação e conta sem perder zeros", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    wrap(<SupportOptions links={{ ...none, pix: "chave", transfer: {
      bank: "Banco de teste", recipient: "Pessoa de teste", branch: "0123",
      operation: "0037", account: "000123456789-0",
    } }} />);
    expect(screen.getAllByRole("heading").map(h => h.textContent)).toEqual(["PIX", "Transferência bancária"]);
    expect(screen.getByText("000123456789-0")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Copiar dados bancários" }));
    expect(await screen.findByText("Dados bancários copiados.")).toBeTruthy();
    expect(writeText).toHaveBeenCalledWith("Banco: Banco de teste\nDestinatário: Pessoa de teste\nAgência: 0123\nOperação: 0037\nConta: 000123456789-0");
    expect(screen.queryByText("Chave copiada.")).toBeNull();
  });

  it("mantém os dados bancários disponíveis para cópia manual quando a área de transferência falha", async () => {
    Object.defineProperty(navigator, "clipboard", { value: { writeText: vi.fn().mockRejectedValue(new Error("Sem permissão")) }, configurable: true });
    wrap(<SupportOptions links={{ ...none, transfer: {
      bank: "Banco de teste", recipient: "Pessoa de teste", branch: "0123",
      operation: null, account: "000123456789-0",
    } }} />);
    expect(screen.queryByText(/As contas de doação/)).toBeNull();
    expect(screen.queryByText("Operação")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Copiar dados bancários" }));
    expect(await screen.findByText(/Selecione os dados e copie manualmente/)).toBeTruthy();
    expect(screen.getByText("000123456789-0")).toBeTruthy();
  });
});

describe("PeriodFilter (ADR-0026)", () => {
  it("monta Ano › Semestre › Trimestre e marca todas as folhas ao marcar o ano", async () => {
    const { PeriodFilter, buildPeriodTree } = await import("./PeriodFilter");
    const leaves = ["2024T3", "2024T4", "2025T1", "2025T2"];
    const tree = buildPeriodTree(leaves);
    expect(tree.map((n) => n.code)).toEqual(["2025", "2024"]);
    expect(tree[0]?.children.map((n) => n.code)).toEqual(["2025S1"]);
    expect(tree[0]?.children[0]?.children.map((n) => n.code)).toEqual(["2025T1", "2025T2"]);
    const onChange = vi.fn();
    wrap(<PeriodFilter leaves={leaves} complete={leaves} selected={["2025T2"]} onChange={onChange} />);
    const year = screen.getByRole("checkbox", { name: "2025" }) as HTMLInputElement;
    expect(year.indeterminate).toBe(true);
    fireEvent.click(year);
    expect(onChange).toHaveBeenLastCalledWith(["2025T1", "2025T2"]);
    fireEvent.click(screen.getByRole("checkbox", { name: "2024" }));
    expect(onChange).toHaveBeenLastCalledWith(["2024T3", "2024T4", "2025T2"]);
    // O nome escolhe só aquele período (troca rápida).
    fireEvent.click(screen.getByRole("button", { name: "Só T1 2025" }));
    expect(onChange).toHaveBeenLastCalledWith(["2025T1"]);
  });

  it("Acumular só em fluxos e variações %; taxas ficam com o botão desabilitado", () => {
    const months = ["2025M11", "2025M12"];
    const base = allKpis(navFixture)[0]!;
    const grains = [
      { grain: "mes", label: "Mês", periods: months, complete_periods: months },
      { grain: "ano", label: "Ano", periods: ["2025"], complete_periods: [] },
    ];
    const common = { nav: navFixture, dimensions: [], onKpi: vi.fn(), onDimensions: vi.fn(), level: "uf", selection: ["2025M12"], grain: null, onLevel: vi.fn(), onPeriods: vi.fn(), onGrain: vi.fn(), onClear: vi.fn(), canClear: false, onIsolate: vi.fn(), onAccumulate: vi.fn() };
    wrap(<Sidebar {...common} kpi={{ ...base, periods: months, time_grains: grains, time_aggregation: "sum" }} />);
    expect((screen.getByRole("checkbox", { name: "Acumular" }) as HTMLInputElement).disabled).toBe(false);
    cleanup();
    wrap(<Sidebar {...common} kpi={{ ...base, periods: months, time_grains: grains, time_aggregation: "mean" }} />);
    expect((screen.getByRole("checkbox", { name: "Acumular" }) as HTMLInputElement).disabled).toBe(true);
  });
});

describe("Exportação (B5)", () => {
  it("permite 200 mil somente nos dois KPIs LSPA e usa 10 mil após a janela D6", async () => {
    const { exportRowLimit } = await import("./ExportMenu");
    expect(exportRowLimit("safra_estimada")).toBe(200_000);
    expect(exportRowLimit("safra_area_colhida")).toBe(200_000);
    for (const variable of [498, 513, 516, 525, 543, 6575]) {
      expect(exportRowLimit(`pib_municipios_v${variable}`)).toBe(10_000);
    }
    expect(exportRowLimit("populacao_residente")).toBe(10_000);
  });
  it("estima as linhas por nível, período e combinação de categorias", async () => {
    const { estimateRows } = await import("./ExportMenu");
    const kpi = {
      ...allKpis(navFixture)[0]!,
      periods: ["2024T1", "2024T2"],
      time_grains: [
        { grain: "trimestre", label: "Trimestre", periods: ["2024T1", "2024T2"], complete_periods: [] },
        { grain: "ano", label: "Ano", periods: ["2024"], complete_periods: [] },
      ],
      dimensions: [
        { classification_id: "c2", label: "Sexo", categories: [{ category_key: "c2:4" }, { category_key: "c2:5" }] },
      ],
    } as unknown as Kpi;
    // UF (27) × (2 trimestres + 1 ano) × (Total + 2 sexos)
    expect(estimateRows(kpi, ["uf"], ["trimestre", "ano"], ["c2"], true, { counts: { uf: 27 }, periods: {} })).toBe(27 * 3 * 3);
    expect(estimateRows(kpi, ["brasil", "uf"], ["trimestre"], [], true, { counts: { brasil: 1, uf: 27 }, periods: {} })).toBe(28 * 2);
  });

  it("usa a cobertura de cada nível em todos os períodos e a seleção comum no recorte", async () => {
    const { estimateRows } = await import("./ExportMenu");
    const kpi: Kpi = {
      ...allKpis(navFixture)[0]!,
      periods: ["2002", "2008", "2018"],
      periods_by_level: { uf: ["2002", "2008", "2018"], municipio: ["2008"] },
      time_grains: [],
    };
    const counts = { uf: 1, municipio: 645 };
    expect(estimateRows(kpi, ["uf", "municipio"], ["ano"], [], true, { counts, periods: {} })).toBe(648);
    expect(estimateRows(kpi, ["uf", "municipio"], ["ano"], [], true, { counts, periods: { ano: ["2008"] } })).toBe(646);
  });
});

describe("Tabela dinâmica (B6)", () => {
  it("desenha cabeçalhos de linhas e colunas e troca os campos", async () => {
    const { PivotControls, PivotTable } = await import("./PivotTable");
    const data = {
      kpi_id: "k",
      indicator_id: "i",
      level: "regiao",
      unit: "Pessoas",
      row_fields: [
        { id: "territorio", label: "Território" },
        { id: "c2", label: "Sexo" },
      ],
      col_fields: [{ id: "periodo", label: "Período" }],
      rows: [
        { keys: ["regiao:5", "c2:total"], labels: ["Centro-Oeste", "Total"] },
        { keys: ["regiao:5", "c2:4"], labels: ["Centro-Oeste", "Homens"] },
      ],
      columns: [
        { keys: ["2010"], labels: ["2010"] },
        { keys: ["2022"], labels: ["2022"] },
      ],
      cells: [
        [{ value: 14058094, status: "valid" }, { value: 16289538, status: "valid" }],
        [{ value: 6979971, status: "valid" }, null],
      ],
      provenance: { release_id: "r", tables: [], derived: false, truncated: false },
    } as unknown as Pivot;
    const onSelect = vi.fn();
    wrap(<PivotTable data={data} totals={{ c2: "c2:total" }} shares selected={null} onSelect={onSelect} />);
    // Padrão: ordenada pelo último período (maior primeiro); sem agrupamento visual.
    expect(screen.getAllByRole("rowheader").map((h) => h.textContent)).toEqual(["Centro-Oeste", "Total", "Centro-Oeste", "Homens"]);
    // % do Total das categorias, no mesmo território e período.
    expect(screen.getAllByRole("cell")[2]?.textContent).toContain("(49,7%)");
    // Na ordem da API (clique no campo das linhas), os rótulos repetidos ficam em branco.
    fireEvent.click(screen.getByRole("button", { name: "Ordenar por Território" }));
    expect(screen.getAllByRole("rowheader").map((h) => h.textContent)).toEqual(["Centro-Oeste", "Total", "", "Homens"]);
    fireEvent.click(screen.getAllByRole("row")[2]!);
    expect(onSelect).toHaveBeenCalledWith("regiao:5");
    expect(screen.getByRole("columnheader", { name: /2022/ })).toBeTruthy();
    expect(screen.getAllByRole("cell").at(-1)?.textContent).toBe("sem dado");
    cleanup();
    const onChange = vi.fn();
    const fields = [
      { id: "territorio", label: "Território" },
      { id: "periodo", label: "Período" },
      { id: "c2", label: "Sexo" },
    ];
    wrap(<PivotControls fields={fields} rows={["territorio"]} cols={["periodo"]} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Trocar linhas e colunas" }));
    expect(onChange).toHaveBeenLastCalledWith(["periodo"], ["territorio"]);
    fireEvent.change(screen.getByRole("combobox", { name: "Adicionar campo em Linhas" }), { target: { value: "c2" } });
    expect(onChange).toHaveBeenLastCalledWith(["territorio", "c2"], ["periodo"]);
  });
});

describe("Tabela dinâmica (DS 2.9): % por, linha de totais e aviso no botão i", () => {
  const base = {
    kpi_id: "k",
    indicator_id: "i",
    level: "uf",
    unit: "Pessoas",
    row_fields: [{ id: "territorio", label: "Território" }],
    provenance: { release_id: "r", tables: [], derived: false, truncated: false },
  };

  it("calcula o % sobre a linha de totais e ordena pela coluna clicada", async () => {
    const { PivotTable } = await import("./PivotTable");
    const data = {
      ...base,
      col_fields: [{ id: "periodo", label: "Período" }],
      rows: [
        { keys: ["uf:29"], labels: ["Bahia"] },
        { keys: ["uf:21"], labels: ["Maranhão"] },
      ],
      columns: [{ keys: ["2022"], labels: ["2022"] }],
      cells: [[{ value: 30, status: "valid" }], [{ value: 70, status: "valid" }]],
      footer: { keys: ["regiao:2"], labels: ["Nordeste"] },
      footer_cells: [{ value: 200, status: "valid" }],
    } as unknown as Pivot;
    wrap(<PivotTable data={data} totals={{}} shares selected="uf:29" onSelect={vi.fn()} />);
    expect(screen.getAllByRole("rowheader").map((h) => h.textContent)).toEqual(["Maranhão", "Bahia", "Total: Nordeste"]);
    expect(screen.getByRole("row", { selected: true }).textContent).toContain("Bahia");
    fireEvent.change(screen.getByRole("combobox", { name: "Calcular % por" }), { target: { value: "column" } });
    expect(screen.getAllByRole("cell")[0]?.textContent).toContain("(35,0%)");
    fireEvent.click(screen.getByRole("button", { name: "Ordenar por 2022" }));
    expect(screen.getAllByRole("rowheader")[0]?.textContent).toBe("Bahia");
  });

  it("fica vermelho e abre o aviso quando o detalhe veio só com o Total", async () => {
    const { PivotTable, emptyDetails } = await import("./PivotTable");
    const data = {
      ...base,
      col_fields: [{ id: "c664", label: "Estado civil" }],
      rows: [{ keys: ["municipio:1"], labels: ["Aguiar"] }],
      columns: [{ keys: ["c664:0"], labels: ["Total"] }],
      cells: [[{ value: 27, status: "valid" }]],
    } as unknown as Pivot;
    expect(emptyDetails(data, { c664: "c664:0" })).toEqual(["Estado civil"]);
    wrap(
      <PivotTable
        data={data}
        totals={{ c664: "c664:0" }}
        shares
        selected={null}
        onSelect={vi.fn()}
        alerts={["Sexo: a fonte não publica este detalhe por Município. Há detalhe em: Brasil."]}
      />,
    );
    const button = screen.getByRole("button", { name: "Aviso sobre esta tabela" });
    expect(button.className).toContain("is-alert");
    expect(button.getAttribute("aria-expanded")).toBe("true");
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Estado civil: a fonte não traz este detalhe");
    expect(alert.textContent).toContain("Sexo: a fonte não publica este detalhe por Município");
  });

  it("sem aviso, o botão i fica normal e fechado", async () => {
    const { PivotTable } = await import("./PivotTable");
    const data = {
      ...base,
      col_fields: [{ id: "periodo", label: "Período" }],
      rows: [{ keys: ["uf:29"], labels: ["Bahia"] }],
      columns: [{ keys: ["2022"], labels: ["2022"] }],
      cells: [[{ value: 1, status: "valid" }]],
    } as unknown as Pivot;
    wrap(<PivotTable data={data} totals={{}} shares={false} selected={null} onSelect={vi.fn()} />);
    const button = screen.getByRole("button", { name: "Sobre esta tabela" });
    expect(button.className).not.toContain("is-alert");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("combobox", { name: "Calcular % por" })).toBeNull();
  });
});

describe("Barra lateral (DS 2.9, proposta B): indicador no topo e catálogo em painel", () => {
  const kpi = allKpis(navFixture)[0]!;
  const base = {
    nav: navFixture,
    dimensions: [],
    onKpi: vi.fn(),
    onDimensions: vi.fn(),
    level: "uf",
    selection: [],
    grain: null,
    onLevel: vi.fn(),
    onPeriods: vi.fn(),
    onGrain: vi.fn(),
    onClear: vi.fn(),
    canClear: false,
  };

  it("mostra o indicador atual e abre o catálogo com o tema dele; escolher fecha o painel", () => {
    const onKpi = vi.fn();
    wrap(<Sidebar {...base} kpi={kpi} onKpi={onKpi} />);
    expect(document.querySelector(".sb-kpi")?.textContent).toBe(kpi.label);
    const button = screen.getByRole("button", { name: "Trocar indicador" });
    fireEvent.click(button);
    const dialog = screen.getByRole("dialog", { name: "Escolher indicador" });
    expect(within(dialog).getByRole("searchbox")).toBe(document.activeElement);
    const themes = within(within(dialog).getByRole("navigation", { name: "Temas" }));
    expect(themes.getAllByRole("button", { pressed: true })).toHaveLength(1);
    const named = (label: string) => (name: string) => name.startsWith(label);
    const current = within(dialog).getByRole("button", { name: named(kpi.label) });
    expect(current.getAttribute("aria-pressed")).toBe("true");
    const other = allKpis(navFixture).find((k) => k.kpi_id !== kpi.kpi_id && k.theme_id === kpi.theme_id)!;
    fireEvent.click(within(dialog).getByRole("button", { name: named(other.label) }));
    expect(onKpi).toHaveBeenCalledWith(other.kpi_id);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("busca em todos os temas pelo número da tabela e fecha com Esc", () => {
    wrap(<Sidebar {...base} kpi={kpi} />);
    fireEvent.click(screen.getByRole("button", { name: "Trocar indicador" }));
    const dialog = screen.getByRole("dialog", { name: "Escolher indicador" });
    fireEvent.change(within(dialog).getByRole("searchbox"), { target: { value: "7972" } });
    expect(dialog.querySelector(".catalog-list")?.textContent).toContain("Tabela 7972");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Trocar indicador" }));
  });

  it("Detalhar por começa recolhido e mostra quantas categorias estão marcadas", () => {
    const withDims = allKpis(navFixture).find((k) => k.dimensions.length > 0)!;
    wrap(<Sidebar {...base} kpi={withDims} dimensions={[withDims.dimensions[0]!.classification_id]} />);
    expect(document.querySelectorAll(".dim-cats")).toHaveLength(0);
    expect(document.querySelector(".dim-filter .check-note")?.textContent).toMatch(/^\d+ de \d+$/);
  });
});
