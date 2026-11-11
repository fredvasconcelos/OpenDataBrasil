import { describe, expect, it } from "vitest";

import { dimensionsText, flatten, highlight, matchKpi, periodRange } from "./catalog";
import { themeVisual } from "./themes";
import { navFixture } from "./fixtures";

describe("catálogo", () => {
  const items = flatten(navFixture);

  it("acha pelo nome, pelo tema e pelo número da tabela, sem acentos", () => {
    const pop = items.find((i) => i.kpi.kpi_id === "populacao_estimada")!;
    expect(matchKpi(pop, "POPULACAO")).toBe("label");
    expect(matchKpi(pop, "demografia")).toBe("theme");
    expect(matchKpi(pop, "6579")).toBe("table");
    expect(matchKpi(pop, "tabela 6579")).toBe("table");
    expect(matchKpi(pop, "fundo de participacao")).toBe("description");
    expect(matchKpi(pop, "ipca")).toBeNull();
  });

  it("marca o termo preservando os acentos do texto", () => {
    expect(highlight("População estimada", "popula")).toEqual([
      { text: "Popula", hit: true },
      { text: "ção estimada", hit: false },
    ]);
  });

  it("resume os períodos e as dimensões", () => {
    expect(periodRange(["2001", "2002", "2026"])).toBe("2001–2026 (3)");
    expect(periodRange([])).toBe("—");
    const censo = items.find((i) => i.kpi.kpi_id === "populacao_residente")!.kpi;
    expect(dimensionsText(censo)).toEqual({ main: "Cor ou raça", others: "Sexo" });
  });

  it("dá ícone e família de cor pelo rótulo do tema; desconhecido usa o genérico", () => {
    expect(themeVisual({ label: "Saúde" })).toEqual({ family: "magenta", icon: "saude" });
    expect(themeVisual({ label: "POPULAÇÃO E DEMOGRAFIA" })).toEqual({ family: "azul", icon: "pessoas" });
    expect(themeVisual({ label: "Tema novo" })).toEqual({ family: "ardosia", icon: "generico" });
  });
});
