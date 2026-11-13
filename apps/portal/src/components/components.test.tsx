import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import type { Detail, DetailNode, GeoCollection, Kpi, Navigation, Series, Table } from "../lib/types";
import { DataTable } from "./DataTable";
import { DetailTooltip } from "./DetailTooltip";
import { navFixture } from "../lib/fixtures";
import { allKpis } from "../lib/state";
import { AboutCatalog } from "./AboutCatalog";
import { HomeCatalog } from "./HomeCatalog";
import { KpiInfo } from "./KpiInfo";
import { MapView } from "./MapView";
import { ProjectLinks } from "./ProjectLinks";
import { SeriesChart } from "./SeriesChart";
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

describe("DataTable", () => {
  const table: Table = {
    kpi_id: "k",
    indicator_id: "i",
    level: "uf",
    period: "2022",
    unit: "Pessoas",
    columns: [
      { key: "c2:6794", label: "Total", full_label: "Total", depth: 0, group: "c2:6794", parent: null },
      { key: "c2:4", label: "Homens", full_label: "Homens", depth: 1, group: "c2:4", parent: "c2:6794" },
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

  // Cor ou raça × sexo: Total (com os totais de linha por sexo) e Branca (com o sexo).
  const matrix: Table = {
    ...table,
    columns: [
      { key: "T|T", label: "Total", full_label: "Total", depth: 0, group: "T|T", parent: null },
      { key: "T|h", label: "Homens", full_label: "Homens", depth: 1, group: "T|T", parent: "T|T" },
      { key: "T|m", label: "Mulheres", full_label: "Mulheres", depth: 1, group: "T|T", parent: "T|T" },
      { key: "b|T", label: "Branca", full_label: "Branca", depth: 1, group: "b|T", parent: "T|T" },
      { key: "b|h", label: "Branca › Homens", full_label: "Branca › Homens", depth: 2, group: "b|T", parent: "b|T" },
      { key: "b|m", label: "Branca › Mulheres", full_label: "Branca › Mulheres", depth: 2, group: "b|T", parent: "b|T" },
    ],
    rows: [
      {
        geography_key: "uf:29",
        name: "Bahia",
        uf_abbreviation: "BA",
        cells: Object.fromEntries(
          Object.entries({ "T|T": 200, "T|h": 90, "T|m": 110, "b|T": 50, "b|h": 20, "b|m": 30 }).map(([k, v]) => [k, { value: v, status: "valid" }]),
        ),
      },
    ],
    footer: {
      geography_key: "regiao:2",
      name: "Nordeste",
      uf_abbreviation: null,
      cells: Object.fromEntries(
        Object.entries({ "T|T": 1000, "T|h": 480, "T|m": 520, "b|T": 250, "b|h": 100, "b|m": 150 }).map(([k, v]) => [k, { value: v, status: "valid" }]),
      ),
    },
    total_rows: 1,
    limit: 100,
  };

  it("agrupa pela primeira dimensão, com totais de linha e a linha de totais", () => {
    const { container } = wrap(
      <DataTable data={matrix} additive selected={null} sort="value" order="desc" onSort={vi.fn()} onPage={vi.fn()} onSelect={vi.fn()} />,
    );
    const heads = [...container.querySelectorAll("thead th")].map((th) => th.firstChild?.textContent);
    expect(heads).toEqual(["Território", "Total ↓", "Branca"]);
    const bahia = container.querySelectorAll("tbody td");
    // Total: 200, com Homens 90 (45%) e Mulheres 110 (55%) da linha.
    expect(bahia[0]?.textContent).toContain("Homens90 (45,0%)");
    // Branca: 50 (25% do território); Homens 20 (10% do território).
    expect(bahia[1]?.textContent).toContain("50 (25,0%)");
    expect(bahia[1]?.textContent).toContain("Homens20 (10,0%)");
    // Grupo: Homens dentro de Branca = 40%.
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "group" } });
    expect(container.querySelectorAll("tbody td")[1]?.textContent).toContain("Homens20 (40,0%)");
    // Coluna: a Bahia tem 20% da população branca do Nordeste (50 de 250).
    expect(screen.getByRole("option", { name: "Coluna (Nordeste)" })).toBeTruthy();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "column" } });
    expect(container.querySelectorAll("tbody td")[1]?.textContent).toContain("50 (20,0%)");
    // Total geral: 50 de 1.000 = 5%.
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "overall" } });
    expect(container.querySelectorAll("tbody td")[1]?.textContent).toContain("50 (5,0%)");
    expect(container.querySelector("tfoot")?.textContent).toContain("Total: Nordeste");
  });

  it("recolhe grupos com muitas linhas e expande pelo cabeçalho", () => {
    const many = Array.from({ length: 13 }, (_, i) => ({ key: `b|${i}`, label: `Branca › Item ${i}`, full_label: `Branca › Item ${i}`, depth: 2, group: "b|T", parent: "b|T" }));
    const { container } = wrap(
      <DataTable data={{ ...matrix, columns: [...matrix.columns.slice(0, 4), ...many] }} additive selected={null} sort="value" order="desc" onSort={vi.fn()} onPage={vi.fn()} onSelect={vi.fn()} />,
    );
    expect(container.querySelectorAll("tbody td")[1]?.textContent).not.toContain("Item 0");
    fireEvent.click(screen.getByRole("button", { name: "+ 13 detalhes" }));
    expect(container.querySelectorAll("tbody td")[1]?.textContent).toContain("Item 0");
  });

  it("rótulos curtos: o ícone de informação mostra o nome completo das colunas", () => {
    const short: Table = {
      ...table,
      columns: [
        { key: "t", label: "Total", full_label: "Total", depth: 0, group: "t", parent: null },
        { key: "a", label: "Rede geral: forma principal", full_label: "Possui ligação à rede geral e a utiliza como forma principal", depth: 1, group: "a", parent: "t" },
      ],
    };
    const { container } = wrap(
      <DataTable data={short} additive selected={null} sort="value" order="desc" onSort={vi.fn()} onPage={vi.fn()} onSelect={vi.fn()} />,
    );
    expect(container.querySelector("thead")?.textContent).toContain("Rede geral: forma principal");
    expect(screen.queryByRole("note")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Sobre esta tabela" }));
    const note = screen.getByRole("note");
    expect(note.textContent).toContain("Possui ligação à rede geral e a utiliza como forma principal");
    expect(note.textContent).toContain("pessoas");
  });

  it("sem KPI aditivo, não mostra % nem a escolha da base", () => {
    const { container } = wrap(
      <DataTable data={matrix} selected={null} sort="value" order="desc" onSort={vi.fn()} onPage={vi.fn()} onSelect={vi.fn()} />,
    );
    expect(container.querySelector(".share")).toBeNull();
    expect(container.querySelector(".share-base select")).toBeNull();
    expect(screen.getByRole("button", { name: "Sobre esta tabela" })).toBeTruthy();
    expect(container.textContent).not.toContain("Calcular % por");
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
    wrap(<AboutCatalog nav={navFixture} releaseId="81f68da1-6c5f" activated={null} licenseReview="requires_review" />);
    expect(screen.getByText("Licença: requires_review")).toBeTruthy();
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
    period: "2022",
    grain: null,
    onLevel: vi.fn(),
    onPeriod: vi.fn(),
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
    wrap(<Sidebar {...props} kpi={flow} period="2025T4" grain="trimestre" onGrain={onGrain} />);
    const group = screen.getByRole("group", { name: "Período por" });
    expect(within(group).getAllByRole("radio").map((r) => (r as HTMLInputElement).checked)).toEqual([false, true, false]);
    expect(within(screen.getByRole("combobox", { name: "Período" })).getByRole("option").textContent).toBe("T4 2025");
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
  it("mostra Contato e o botão do GitHub com rótulo acessível no cabeçalho", () => {
    const { container } = wrap(<ProjectLinks variant="header" contactUrl="mailto:contato@exemplo.org" repoUrl="https://github.com/org/repo" />);
    expect(screen.getByText("Contato").closest("a")?.getAttribute("href")).toBe("mailto:contato@exemplo.org");
    const repo = screen.getByRole("link", { name: "Repositório do projeto no GitHub" });
    expect(repo.getAttribute("target")).toBe("_blank");
    expect(repo.getAttribute("rel")).toContain("noopener");
    expect(container.querySelector("svg[viewBox='0 0 16 16']")).toBeTruthy();
  });

  it("escreve 'Código no GitHub' no rodapé e esconde o que não foi configurado", () => {
    wrap(<ProjectLinks variant="footer" contactUrl={null} repoUrl="https://github.com/org/repo" />);
    expect(screen.getByRole("link", { name: "Código no GitHub" })).toBeTruthy();
    expect(screen.queryByText("Contato")).toBeNull();
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
  const props = { dimensions: [], onDimensions: vi.fn(), level: "", period: "", grain: null, onLevel: vi.fn(), onPeriod: vi.fn(), onGrain: vi.fn(), onClear: vi.fn(), canClear: false };

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
        period="2022"
        grain={null}
        onLevel={vi.fn()}
        onPeriod={vi.fn()}
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
