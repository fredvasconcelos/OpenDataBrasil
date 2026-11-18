// Componentes da página Métricas (DS 2.12, ADR-0027): teclado e aria-*. Os valores e a
// geometria abaixo são EXEMPLOS de teste (quadrados no lugar das UFs), nunca usados na
// página publicada.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "../../messages/pt-BR.json";
import { buildRankingTree, type DatasetItem, type GeoItem } from "../lib/metrics";
import type { GeoCollection } from "../lib/types";
import { AccessMap } from "./AccessMap";
import { AccessRanking } from "./AccessRanking";
import { AccessTable } from "./AccessTable";
import { MetricsPeriod } from "./MetricsPeriod";
import { TopDatasets } from "./TopDatasets";

afterEach(cleanup);

const wrap = (ui: React.ReactNode) =>
  render(
    <NextIntlClientProvider locale="pt-BR" timeZone="America/Sao_Paulo" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  );

const geo = (geography_key: string, name: string, views: number | null, status: GeoItem["status"] = "ok"): GeoItem => ({
  geography_key,
  name,
  views,
  share_pct: views === null ? null : views / 10,
  status,
});

const exemploPaises = [geo("pais:BR", "Brasil", 900), geo("pais:PT", "Portugal", 40)];
const exemploRegioes = [geo("regiao:3", "Sudeste", 600), geo("regiao:2", "Nordeste", 200)];
const exemploUfs = [geo("uf:35", "São Paulo", 350), geo("uf:33", "Rio de Janeiro", 250), geo("uf:29", "Bahia", null, "suprimido")];

describe("AccessRanking", () => {
  const tree = buildRankingTree(exemploPaises, exemploRegioes, exemploUfs);

  it("abre e fecha os nós com aria-expanded e leva o mapa ao lugar escolhido", () => {
    const onSelect = vi.fn();
    wrap(<AccessRanking nodes={tree} selected={null} onSelect={onSelect} />);
    // O Brasil começa aberto (regiões visíveis); o Sudeste começa fechado.
    expect(screen.getByRole("button", { name: "Fechar Brasil" }).getAttribute("aria-expanded")).toBe("true");
    const sudeste = screen.getByRole("button", { name: "Abrir Sudeste" });
    expect(sudeste.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("button", { name: /São Paulo/ })).toBeNull();
    fireEvent.click(sudeste);
    expect(screen.getByRole("button", { name: "Fechar Sudeste" }).getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: /São Paulo/ }));
    expect(onSelect).toHaveBeenCalledWith("uf:35");
  });

  it("abre o caminho até o lugar escolhido no mapa e marca a linha ativa", () => {
    wrap(<AccessRanking nodes={tree} selected="uf:29" onSelect={() => undefined} />);
    const bahia = screen.getByRole("button", { name: /Bahia/ });
    expect(bahia.getAttribute("aria-current")).toBe("true");
    expect(bahia.textContent).toContain("menos de 5");
    expect(bahia.closest(".rank-row")?.classList.contains("is-active")).toBe(true);
  });
});

describe("MetricsPeriod", () => {
  it("marca o período ativo e troca pelos atalhos", () => {
    const onChange = vi.fn();
    wrap(<MetricsPeriod value={{ period: "30d" }} onChange={onChange} />);
    const group = screen.getByRole("group", { name: "Período" });
    expect(within(group).getByRole("button", { name: "30 dias" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(within(group).getByRole("button", { name: "7 dias" }));
    expect(onChange).toHaveBeenCalledWith({ period: "7d" });
  });

  it("no personalizado, só aplica um intervalo válido e anuncia o erro", () => {
    const onChange = vi.fn();
    wrap(<MetricsPeriod value={{ period: "30d" }} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Personalizado" }));
    fireEvent.change(screen.getByLabelText("De"), { target: { value: "2026-11-16" } });
    fireEvent.change(screen.getByLabelText("Até"), { target: { value: "2026-11-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Aplicar" }));
    expect(screen.getByRole("alert").textContent).toBe("A data inicial vem depois da final.");
    expect(screen.getByLabelText("De").getAttribute("aria-invalid")).toBe("true");
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("De"), { target: { value: "2026-10-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Aplicar" }));
    expect(onChange).toHaveBeenCalledWith({ period: "custom", from: "2026-10-01", to: "2026-11-01" });
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("TopDatasets", () => {
  const exemplo: DatasetItem[] = [
    { kpi_id: "populacao_estimada", title: "População estimada", theme: "População e demografia", views: 4120, downloads: 310, api_calls: null },
  ];

  it("troca a ordem e leva o indicador ao Painel", () => {
    const onSort = vi.fn();
    wrap(<TopDatasets items={exemplo} sort="views" onSort={onSort} period="1 de nov. de 2026 – 16 de nov. de 2026" />);
    expect(screen.getByRole("button", { name: "Mais visualizados" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Mais baixados" }));
    expect(onSort).toHaveBeenCalledWith("downloads");
    expect(screen.getByRole("link", { name: "População estimada" }).getAttribute("href")).toBe("/dashboard?kpi=populacao_estimada");
    expect(screen.getByRole("columnheader", { name: "Visualizações" }).getAttribute("aria-sort")).toBe("descending");
    expect(screen.getByText("4.120")).toBeTruthy();
  });

  it("sem indicadores acima do limiar, diz isso em vez de mostrar zeros", () => {
    wrap(<TopDatasets items={[]} sort="views" onSort={() => undefined} period="" />);
    expect(screen.getByText("Nenhum indicador com 5 ou mais acessos no período.")).toBeTruthy();
  });
});

describe("AccessTable", () => {
  it("mostra os mesmos valores do mapa, do maior para o menor, e seleciona pelo teclado", () => {
    const onSelect = vi.fn();
    wrap(<AccessTable items={exemploUfs} levelLabel="Estado" selected="uf:33" onSelect={onSelect} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((r) => within(r).getByRole("rowheader").textContent)).toEqual(["São Paulo", "Rio de Janeiro", "Bahia"]);
    expect(within(rows[2] as HTMLElement).getByText("menos de 5")).toBeTruthy();
    expect(rows[1]?.classList.contains("is-active")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Bahia" }));
    expect(onSelect).toHaveBeenCalledWith("uf:29");
  });
});

describe("AccessMap", () => {
  const square = (x: number, y: number): GeoJSON.Polygon => ({
    type: "Polygon",
    coordinates: [
      [
        [x, y],
        [x + 2, y],
        [x + 2, y + 2],
        [x, y + 2],
        [x, y],
      ],
    ],
  });
  const exemploUfGeo: GeoCollection = {
    type: "FeatureCollection",
    metadata: { release_id: "exemplo", level: "uf", within: null },
    features: [
      { type: "Feature", id: "uf:35", properties: { name: "São Paulo", uf: "SP" }, geometry: square(-50, -24) },
      { type: "Feature", id: "uf:33", properties: { name: "Rio de Janeiro", uf: "RJ" }, geometry: square(-44, -23) },
      { type: "Feature", id: "uf:29", properties: { name: "Bahia", uf: "BA" }, geometry: square(-42, -14) },
    ],
  };

  it("põe um botão por estado, com bandeira, rótulo acessível e tooltip no foco", () => {
    const onActivate = vi.fn();
    wrap(
      <AccessMap
        level="uf"
        items={exemploUfs}
        regions={null}
        ufs={exemploUfGeo}
        within="pais:BR"
        selected="uf:35"
        period="1 de nov. de 2026 – 16 de nov. de 2026"
        onActivate={onActivate}
      />,
    );
    const sp = screen.getByRole("button", { name: "São Paulo: 350 visualizações" });
    expect(sp.getAttribute("aria-pressed")).toBe("true");
    expect(sp.querySelector("img")?.getAttribute("src")).toBe("/bandeiras-uf/sp.svg");
    expect(screen.getByRole("button", { name: "Bahia: menos de 5" })).toBeTruthy();
    fireEvent.focus(sp);
    const tip = screen.getByRole("tooltip");
    expect(within(tip).getByText("São Paulo")).toBeTruthy();
    expect(within(tip).getByText("35,0% do total")).toBeTruthy();
    fireEvent.click(sp);
    expect(onActivate).toHaveBeenCalledWith("uf:35");
    // Controles com aria-label; o "−" começa desativado (sem zoom).
    expect(screen.getByRole("button", { name: "Afastar" }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("group", { name: "Legenda do mapa" })).toBeTruthy();
  });

  it("no globo, mostra o ponto com a bandeira do país e o Brasil em destaque", () => {
    const { container } = wrap(
      <AccessMap level="pais" items={exemploPaises} regions={null} ufs={null} within={null} selected={null} period="" onActivate={() => undefined} />,
    );
    const br = screen.getByRole("button", { name: "Brasil: 900 visualizações" });
    expect(br.querySelector(".fi-br")).toBeTruthy();
    expect(container.querySelector('path[fill="var(--odbr-primary)"]')).toBeTruthy();
    expect(screen.getByText("Limites: Natural Earth · IBGE")).toBeTruthy();
  });
});
