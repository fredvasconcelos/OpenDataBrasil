import { describe, expect, it } from "vitest";

import { periodAlerts, pointAt, toMapValues, toSeries } from "./adapt";
import { brl, brlShort, periodLabel, periodsLabel, seat, share } from "./format";
import type { ContasMap, ContasSeries } from "./types";
import { classIcon, functionVisual } from "./visual";

const provenance = { release_id: "e8bb048c", tables: [], periods: ["2026M10", "2026M11"], partial: true,
  period_notes: [
    { period: "2026M11", status: "aberto" as const, note: "Último mês publicado" },
    { period: "2026M03", status: "incompleto" as const, note: "Faltam ações", shortfall_share: 0.07, missing_actions: [] },
    { period: "2025M12", status: "fechado" as const, note: "" },
  ] };

const series: ContasSeries = {
  lens: "A", geography_key: "uf:25", grain: "mes", dimension: null,
  lines: [{ category_code: "total", label: "Total", points: [{ period: "2026M10", value: 798745718.17 }, { period: "2026M11", value: 427741854.76 }] }],
  provenance,
} as unknown as ContasSeries;

describe("format", () => {
  it("R$ completo e abreviado, sem arredondar o dado", () => {
    expect(brl(2026675609.95)).toBe("R$ 2.026.675.609,95");
    expect(brlShort(25651839651.83)).toBe("R$ 25,7 bi");
    expect(brlShort(812_000_000)).toBe("R$ 812,0 mi");
    expect(brlShort(45_600)).toBe("R$ 45,6 mil");
  });
  it("participação vem como fração da API", () => {
    expect(share(0.39067717839703014)).toBe("39,1%");
    expect(share(null)).toBe("");
  });
  it("períodos", () => {
    expect(periodLabel("2025M03")).toBe("mar/2025");
    expect(periodLabel("2025T1")).toBe("1º tri/2025");
    expect(periodLabel("2025")).toBe("2025");
    expect(periodsLabel(Array.from({ length: 12 }, (_, i) => `2025M${String(i + 1).padStart(2, "0")}`))).toBe("2025");
    expect(periodsLabel(["2026M01", "2026M11"])).toBe("jan/2026 a nov/2026");
  });
  it("sede", () => {
    expect(seat("JOÃO PESSOA", "PB")).toBe("JOÃO PESSOA/PB");
    expect(seat(null, null)).toBe("—");
  });
});

describe("adaptadores", () => {
  it("mapa: só muda a forma", () => {
    const map = { lens: "A", level: "uf", within: null, dimension: null, categories: [], unit: "R$", total: 10,
      rows: [{ geography_key: "uf:25", name: "Paraíba", value: 25651839651.83 }], provenance } as unknown as ContasMap;
    expect(toMapValues(map)).toEqual([{ geography_key: "uf:25", name: "Paraíba", value: 25651839651.83, status: "valid" }]);
  });
  it("série: mês aberto vira parcial; valores intactos", () => {
    const s = toSeries(series, "Paraíba");
    const pts = s.series[0]!.points;
    expect(pts.map((p) => p.value)).toEqual([798745718.17, 427741854.76]);
    expect(pts.map((p) => p.status)).toEqual(["valid", "partial_period"]);
    expect(s.geography.level_id).toBe("uf");
  });
  it("pointAt devolve o valor da API ou null", () => {
    expect(pointAt(series, "total", "2026M11")).toBe(427741854.76);
    expect(pointAt(series, "total", "2020")).toBeNull();
    expect(pointAt(series, "outra", "2026M11")).toBeNull();
  });
  it("alertas: sem os fechados, em ordem do tempo", () => {
    expect(periodAlerts(provenance.period_notes).map((n) => n.period)).toEqual(["2026M03", "2026M11"]);
    expect(periodAlerts(undefined)).toEqual([]);
  });
});

describe("visual", () => {
  it("função por código, com fallback", () => {
    expect(functionVisual("10").family).toBe("magenta");
    expect(functionVisual("10").icon.name).toBe("heart-pulse");
    expect(functionVisual("99").icon.name).toBe("layer-group");
  });
  it("classe de favorecido", () => {
    expect(classIcon("municipio").name).toBe("city");
    expect(classIcon("pessoa_fisica").name).toBe("user");
    expect(classIcon("desconhecida").name).toBe("circle-question");
  });
});
