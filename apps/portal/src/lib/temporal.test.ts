import { expect, it } from "vitest";

import { navFixture } from "./fixtures";
import type { Kpi, Navigation } from "./types";
import { allKpis, canAccumulate, periodQuery, readState } from "./state";

const quarterly = (): Kpi => ({ ...allKpis(navFixture)[0]!, kpi_id: "trimestral",
  levels: ["brasil"], periods: ["2023T1", "2025T1"], periods_by_level: {},
  time_grains: [{ grain: "trimestre", label: "Trimestre", periods: ["2023T1", "2025T1"], complete_periods: ["2023T1", "2025T1"] }],
  time_aggregation: null, temporal: { isolate: true, accumulate: false, seasonal_sum: false, accumulation_rule: null },
});
const navigation = (kpi: Kpi): Navigation => ({ ...navFixture, themes: [{ theme_id: "t", label: "Tema", filters: [],
  subthemes: [{ subtheme_id: "s", label: "Subtema", planned: [], kpis: [kpi] }] }] });

it("isola trimestral de grão único sem pedir um ano inválido no mapa", () => {
  const kpi = quarterly();
  const state = readState(new URLSearchParams("kpi=trimestral&isolar=1&periodo=2023,2025&acumular=1"), navigation(kpi));
  expect(state.isolate).toBe(true);
  expect(state.accumulate).toBe(false);
  expect(periodQuery(kpi, state).map.period).toBe("2025T1");
});

it("explicita os anos intermediários no acumulado sazonal", () => {
  const kpi = quarterly();
  kpi.temporal = { isolate: true, accumulate: true, seasonal_sum: true, accumulation_rule: "sum" };
  const state = readState(new URLSearchParams("kpi=trimestral&isolar=1&periodo=2023,2025&acumular=1"), navigation(kpi));
  const q = periodQuery(kpi, state);
  expect(q.series.periods).toEqual(["2023", "2024", "2025"]);
  expect(q.series.accumulate).toBeNull();
});

it("não usa a composição cronológica para somar trimestres descontínuos entre anos", () => {
  const kpi = quarterly();
  kpi.temporal = { isolate: true, accumulate: true, seasonal_sum: false, accumulation_rule: "compound" };
  expect(canAccumulate(kpi)).toBe(true);
  expect(canAccumulate(kpi, true)).toBe(false);
});
