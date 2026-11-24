import { describe, expect, it } from "vitest";

import { contasQuery } from "@/lib/api/contas";
import { availablePeriods, defaultPeriod, findState, readContasState } from "./state";
import type { Geography } from "@/lib/types";
import type { ContasMeta } from "./types";

const months = Array.from({ length: 12 }, (_, i) => `2025M${String(i + 1).padStart(2, "0")}`);
const meta: ContasMeta = { release_id: "candidato", recipient_classes: {}, notes: [], lenses: [{ lens: "A", label: "Transferências", description: "", notes: [], dimensions: [], group_by: [], periods: [...months, "2026M01"], latest_period: "2026M01", statuses: [...months.map((period) => ({ period, status: "fechado" as const, note: "" })), { period: "2026M01", status: "aberto", note: "Mês aberto" }] }] };

describe("estado das contas", () => {
  it("encontra UF pela hierarquia oficial, sem inferir pelo código municipal", async () => {
    const node = (key: string, level: string, parent: string | null): Geography => ({ geography_key: key, level_id: level, parent_key: parent, level_name: null, territory_code: key.split(":")[1]!, name: key, uf_abbreviation: null });
    const municipality = node("municipio:2507507", "municipio", "regiao_imediata:250001");
    const parents = [node("regiao_imediata:250001", "regiao_imediata", "uf:25"), node("uf:25", "uf", "regiao:2")];
    const found = await findState(municipality, async (key) => parents.find((p) => p.geography_key === key)!);
    expect(found?.geography_key).toBe("uf:25");
  });
  it("prefere ano integral fechado e oferece somente períodos do release", () => {
    expect(defaultPeriod(meta)).toBe("2025");
    expect(availablePeriods(meta)).toContain("2026M01");
    expect(availablePeriods(meta)).not.toContain("2026M02");
  });
  it("ignora período inexistente e paginação fora do limite", () => {
    const state = readContasState(new URLSearchParams("period=1999&page=NaN"), meta);
    expect(state.period).toBe("2025");
    expect(state.page).toBe(1);
    expect(state.geography).toBe("brasil:1");
  });
  it("preserva território, área, grão e página para recarregar o link", () => {
    expect(readContasState(new URLSearchParams("geography=uf:25&area=10&period=2026M01&grain=ano&page=2"), meta)).toEqual({ geography: "uf:25", area: "10", period: "2026M01", grain: "ano", page: 2 });
  });
  it("cliente envia períodos e categorias como parâmetros repetidos", () => {
    const params = new URLSearchParams(contasQuery({ periods: ["2025M01", "2025M02"], categories: ["10", "12"], within: null }));
    expect(params.getAll("periods")).toEqual(["2025M01", "2025M02"]);
    expect(params.getAll("categories")).toEqual(["10", "12"]);
    expect(params.has("within")).toBe(false);
  });
});
