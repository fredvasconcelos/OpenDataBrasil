// Regras puras da página Métricas (ADR-0027). Os valores abaixo são EXEMPLOS de teste,
// não dados do portal: a página publicada nunca usa fixtures.
import { describe, expect, it } from "vitest";

import {
  buildRankingTree,
  customRangeError,
  formatCount,
  formatPct,
  formatRange,
  geoColors,
  pathTo,
  periodParams,
  regionOfUf,
  viewsText,
  type GeoItem,
} from "./metrics";

const item = (geography_key: string, name: string, views: number | null, status: GeoItem["status"] = "ok"): GeoItem => ({
  geography_key,
  name,
  views,
  share_pct: views === null ? null : views / 10,
  status,
});
const labels = { noAccess: "sem acessos", lessThan: "menos de 5" };

describe("formatação pt-BR", () => {
  it("separa milhares com ponto e decimais com vírgula", () => {
    expect(formatCount(12345)).toBe("12.345");
    expect(formatCount(0)).toBe("0");
    expect(formatPct(12.34)).toBe("12,3%");
    expect(formatPct(0)).toBe("0,0%");
  });

  it("escreve o período por extenso, uma data só quando início e fim coincidem", () => {
    expect(formatRange({ from: "2026-10-18", to: "2026-11-16" })).toMatch(/^18 de out\.? de 2026 – 16 de nov\.? de 2026$/);
    expect(formatRange({ from: "2026-11-16", to: "2026-11-16" })).toMatch(/^16 de nov\.? de 2026$/);
  });

  it("diz 'menos de 5' e 'sem acessos' no lugar do número, nunca zero inventado", () => {
    expect(viewsText(item("uf:35", "São Paulo", 1234), labels)).toBe("1.234");
    expect(viewsText(item("uf:11", "Rondônia", null, "suprimido"), labels)).toBe("menos de 5");
    expect(viewsText(item("uf:12", "Acre", 0, "sem_acessos"), labels)).toBe("sem acessos");
  });
});

describe("período", () => {
  it("valida o intervalo personalizado (datas, ordem e até 366 dias)", () => {
    expect(customRangeError("", "2026-11-16")).toBe("missing");
    expect(customRangeError("2026-11-16", "2026-11-01")).toBe("order");
    expect(customRangeError("2025-01-01", "2026-01-02")).toBe("length");
    expect(customRangeError("2025-11-16", "2026-11-16")).toBeNull();
    expect(customRangeError("2026-11-16", "2026-11-16")).toBeNull();
  });

  it("monta os parâmetros da API", () => {
    expect(periodParams({ period: "30d" })).toEqual({ period: "30d" });
    expect(periodParams({ period: "custom", from: "2026-11-01", to: "2026-11-16" })).toEqual({
      period: "custom",
      from: "2026-11-01",
      to: "2026-11-16",
    });
  });
});

describe("Grandes Regiões", () => {
  it("saem do 1º dígito do código IBGE da UF", () => {
    expect(regionOfUf("uf:11")).toBe("regiao:1");
    expect(regionOfUf("uf:29")).toBe("regiao:2");
    expect(regionOfUf("uf:35")).toBe("regiao:3");
    expect(regionOfUf("uf:43")).toBe("regiao:4");
    expect(regionOfUf("uf:53")).toBe("regiao:5");
    expect(regionOfUf("regiao:3")).toBeNull();
    expect(regionOfUf("pais:BR")).toBeNull();
  });
});

describe("cores por quantis", () => {
  const items = [
    item("uf:35", "São Paulo", 900),
    item("uf:33", "Rio de Janeiro", 500),
    item("uf:31", "Minas Gerais", 300),
    item("uf:41", "Paraná", 120),
    item("uf:11", "Rondônia", null, "suprimido"),
    item("uf:12", "Acre", 0, "sem_acessos"),
  ];
  const { color } = geoColors(items);

  it("pinta zero com --odbr-map-zero e o suprimido com o tom mais claro", () => {
    expect(color(items[5] as GeoItem)).toBe("var(--odbr-map-zero)");
    expect(color(items[4] as GeoItem)).toBe("var(--odbr-seq-1)");
  });

  it("usa a escala sequencial do DS, mais escura para mais acessos", () => {
    const top = color(items[0] as GeoItem);
    const low = color(items[3] as GeoItem);
    expect(top).toMatch(/^var\(--odbr-seq-\d\)$/);
    expect(low).toMatch(/^var\(--odbr-seq-\d\)$/);
    const n = (c: string) => Number(/seq-(\d)/.exec(c)?.[1]);
    expect(n(top)).toBeGreaterThan(n(low));
  });
});

describe("árvore do ranking", () => {
  const countries = [item("pais:PT", "Portugal", 40), item("pais:BR", "Brasil", 900), item("pais:AR", "Argentina", null, "suprimido")];
  const regions = [item("regiao:3", "Sudeste", 600), item("regiao:2", "Nordeste", 200), item("regiao:1", "Norte", 0, "sem_acessos")];
  const ufs = [item("uf:33", "Rio de Janeiro", 250), item("uf:35", "São Paulo", 350), item("uf:29", "Bahia", 200)];
  const tree = buildRankingTree(countries, regions, ufs);

  it("ordena por visualizações, com suprimidos e zeros no fim", () => {
    expect(tree.map((n) => n.key)).toEqual(["pais:BR", "pais:PT", "pais:AR"]);
  });

  it("põe as Grandes Regiões sob o Brasil e cada UF sob a sua região", () => {
    const br = tree[0];
    expect(br?.children.map((n) => n.key)).toEqual(["regiao:3", "regiao:2", "regiao:1"]);
    expect(br?.children[0]?.children.map((n) => n.key)).toEqual(["uf:35", "uf:33"]);
    expect(br?.children[1]?.children.map((n) => n.key)).toEqual(["uf:29"]);
    expect(tree[1]?.children).toEqual([]);
  });

  it("acha o caminho até um lugar (para abrir a árvore)", () => {
    expect(pathTo(tree, "uf:35")).toEqual(["pais:BR", "regiao:3", "uf:35"]);
    expect(pathTo(tree, "pais:PT")).toEqual(["pais:PT"]);
    expect(pathTo(tree, "uf:99")).toEqual([]);
  });
});
