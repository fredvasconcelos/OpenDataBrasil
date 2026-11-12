import { describe, expect, it } from "vitest";

import { formatPeriod, groupedAxis, labelWidth, parsePeriod, parsePeriods, timeTicks, typicalStep } from "./period";

describe("parsePeriod", () => {
  it("lê ano, mês e trimestre", () => {
    expect(parsePeriod("2022")).toMatchObject({ granularity: "year", t: 2022 });
    expect(parsePeriod("202003")).toMatchObject({ granularity: "month", t: 2020 + 2 / 12 });
    expect(parsePeriod("2020-03")).toMatchObject({ granularity: "month" });
    expect(parsePeriod("2026M09")).toMatchObject({ granularity: "month", t: 2026 + 8 / 12 });
    expect(parsePeriod("2026M13")).toBeNull();
    expect(parsePeriod("2020T2")).toMatchObject({ granularity: "quarter", t: 2020.25 });
    expect(parsePeriod("2020-Q4")).toMatchObject({ granularity: "quarter", t: 2020.75 });
    expect(parsePeriod("2020/2021")).toBeNull();
  });

  it("reconhece trimestres SIDRA (AAAA01–04) só quando a lista inteira indica", () => {
    const quarters = parsePeriods(["202201", "202202", "202203", "202204", "202301"]);
    expect(quarters?.every((p) => p.granularity === "quarter")).toBe(true);
    const months = parsePeriods(["202201", "202202", "202205"]);
    expect(months?.every((p) => p.granularity === "month")).toBe(true);
  });

  it("devolve null quando algum código não é reconhecido (eixo ordinal)", () => {
    expect(parsePeriods(["2020", "2021", "safra 21/22"])).toBeNull();
  });

  it("formata o período por extenso", () => {
    expect(formatPeriod({ granularity: "month", unit: 2020 * 12 + 2 })).toBe("mar 2020");
    expect(formatPeriod({ granularity: "quarter", unit: 2020 * 4 })).toBe("T1 2020");
  });
});

describe("timeTicks", () => {
  // Série anual com anos não publicados (2007, 2010, 2022, 2023), como a PNAD.
  const years = [2001, 2002, 2003, 2004, 2005, 2006, 2008, 2009, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2024, 2025, 2026];
  const parsed = parsePeriods(years.map(String)) ?? [];
  const toX = (w: number) => (t: number) => ((t - 2001) / 25) * w;

  it("sempre mostra o primeiro e o último período, ancorados por dentro", () => {
    const { ticks } = timeTicks(parsed, 560, toX(560));
    expect(ticks[0]).toMatchObject({ label: "2001", anchor: "start" });
    expect(ticks.at(-1)).toMatchObject({ label: "2026", anchor: "end" });
  });

  it("usa passos redondos que cabem na largura, sem encostar nas pontas", () => {
    const { ticks, step } = timeTicks(parsed, 560, toX(560));
    expect(step).toBe(5);
    expect(ticks.map((t) => t.label)).toEqual(["2001", "2005", "2010", "2015", "2020", "2026"]);
    const narrow = timeTicks(parsed, 240, toX(240));
    expect(narrow.step).toBeGreaterThanOrEqual(10);
  });

  it("não sobrepõe rótulos", () => {
    for (const w of [200, 320, 480, 900]) {
      const { ticks } = timeTicks(parsed, w, toX(w));
      const boxes = ticks.map((t) => {
        const x = toX(w)(t.t);
        const lw = t.label.length * 7.2;
        return (t.anchor === "start" ? [x, x + lw] : t.anchor === "end" ? [x - lw, x] : [x - lw / 2, x + lw / 2]) as [number, number];
      });
      for (let i = 1; i < boxes.length; i++) expect(boxes[i]![0]).toBeGreaterThan(boxes[i - 1]![1]);
    }
  });

  it("em séries mensais longas rotula só os anos", () => {
    const months = Array.from({ length: 120 }, (_, i) => `${2015 + Math.floor(i / 12)}${String((i % 12) + 1).padStart(2, "0")}`);
    const p = parsePeriods(months) ?? [];
    const x = (t: number) => ((t - 2015) / 10) * 560;
    const { ticks } = timeTicks(p, 560, x);
    expect(ticks[0]?.label).toBe("jan 2015");
    expect(ticks.at(-1)?.label).toBe("dez 2024");
    expect(ticks.slice(1, -1).every((t) => /^\d{4}$/.test(t.label))).toBe(true);
  });
});

describe("typicalStep", () => {
  it("é a mediana dos passos (vãos ficam acima de 1,5×)", () => {
    expect(typicalStep(parsePeriods(["2000", "2001", "2002", "2005", "2006"]) ?? [])).toBe(1);
    expect(typicalStep(parsePeriods(["1991", "2000", "2010", "2022"]) ?? [])).toBe(10);
  });
});

describe("groupedAxis (trimestres e semestres em duas linhas)", () => {
  const scale = (from: number, to: number, x0: number, x1: number) => (t: number) => x0 + ((t - from) / (to - from)) * (x1 - x0);

  it("semestres: S1 e S2 em cima, o ano centralizado embaixo, divisória entre anos", () => {
    const ps = parsePeriods(["2025S1", "2025S2", "2026S1"])!;
    const toX = scale(ps[0]!.t, ps[2]!.t, 0, 400);
    const axis = groupedAxis(ps, 0, 400, toX);
    expect(axis.parts.map((p) => p.label)).toEqual(["S1", "S2", "S1"]);
    expect(axis.years.map((y) => y.label)).toEqual(["2025", "2026"]);
    expect(axis.bounds).toHaveLength(1);
    // O ano fica no meio do trecho dos seus semestres.
    expect(axis.years[0]!.x).toBeCloseTo((axis.parts[0]!.x + axis.parts[1]!.x) / 2);
  });

  it("muitos trimestres: some a linha de cima e o ano pula num passo que caiba", () => {
    const raws = Array.from({ length: 47 }, (_, i) => `${2015 + Math.floor(i / 4)}T${(i % 4) + 1}`);
    const ps = parsePeriods(raws)!;
    const toX = scale(ps[0]!.t, ps.at(-1)!.t, 0, 300);
    const axis = groupedAxis(ps, 0, 300, toX);
    expect(axis.parts).toEqual([]);
    const shown = axis.years.filter((y) => y.label);
    expect(shown.length).toBeGreaterThan(1);
    expect(shown.length).toBeLessThan(12);
  });

  it("ano corrente com poucos trimestres não encosta no anterior", () => {
    const raws = Array.from({ length: 58 }, (_, i) => `${2012 + Math.floor(i / 4)}T${(i % 4) + 1}`);
    const ps = parsePeriods(raws)!;
    const toX = scale(ps[0]!.t, ps.at(-1)!.t, 0, 640);
    const shown = groupedAxis(ps, 0, 640, toX, 8, false).years.filter((y) => y.label);
    for (let i = 1; i < shown.length; i++) expect(shown[i]!.x - shown[i - 1]!.x).toBeGreaterThanOrEqual(labelWidth("2026") + 8);
  });

  it("ano e mês não usam o eixo agrupado", () => {
    const ps = parsePeriods(["2024M01", "2024M02"])!;
    expect(groupedAxis(ps, 0, 100, (t) => t)).toEqual({ parts: [], years: [], bounds: [] });
  });
});
