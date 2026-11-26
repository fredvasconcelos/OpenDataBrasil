import { describe, expect, it } from "vitest";

import { contasQuery } from "@/lib/api/contas";
import { availablePeriods, defaultPeriod, findState, panelHref, readContasState, readFederalState, safePanelHref } from "./state";
import type { Geography } from "@/lib/types";
import type { ContasMeta } from "./types";

const months = Array.from({ length: 12 }, (_, i) => `2025M${String(i + 1).padStart(2, "0")}`);
const meta: ContasMeta = { release_id: "candidato", recipient_classes: {}, notes: [], lenses: [{ lens: "A", label: "Transferências", description: "", notes: [], dimensions: [], group_by: [], periods: [...months, "2026M01"], latest_period: "2026M01", statuses: [...months.map((period) => ({ period, status: "fechado" as const, note: "" })), { period: "2026M01", status: "aberto", note: "Mês aberto" }] }] };

describe("estado das contas", () => {
  it("retorno da ficha mantém filtros e exclui parâmetros estranhos", () => {
    const query = new URLSearchParams("geography=uf:25&period=2025&area=10&page=2&grain=ano&extra=ignorar");
    const back = panelHref(query);
    expect(safePanelHref(back)).toBe(back);
    expect(new URL(back, "https://portal.invalid").searchParams.get("page")).toBe("2");
    expect(back).not.toContain("extra");
  });
  it("retorno da ficha rejeita destinos externos e outras rotas", () => {
    for (const value of ["https://exemplo.org/contas/painel", "//exemplo.org", "/sobre", "/contas/painel-outra", undefined]) {
      expect(safePanelHref(value)).toBe("/contas/painel");
    }
  });
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
    expect(readContasState(new URLSearchParams("geography=uf:25&area=10&period=2026M01&grain=ano&page=2&order=name"), meta)).toEqual({ geography: "uf:25", area: "10", period: "2026M01", grain: "ano", page: 2, order: "name" });
  });
  it("cliente envia períodos e categorias como parâmetros repetidos", () => {
    const params = new URLSearchParams(contasQuery({ periods: ["2025M01", "2025M02"], categories: ["10", "12"], within: null }));
    expect(params.getAll("periods")).toEqual(["2025M01", "2025M02"]);
    expect(params.getAll("categories")).toEqual(["10", "12"]);
    expect(params.has("within")).toBe(false);
  });
});


describe("lentes federais", () => {
  const federal: ContasMeta = { ...meta, lenses: [...meta.lenses,
    { ...meta.lenses[0]!, lens: "B", periods: ["2024M01"], latest_period: "2024M01", statuses: [], group_by: [{ id: "recipient", label: "Favorecido" }, { id: "territory", label: "Território" }], dimensions: [{ id: "organ", label: "Órgão" }] },
    { ...meta.lenses[0]!, lens: "C", periods: ["2023M01"], latest_period: "2023M01", statuses: [], dimensions: [{ id: "function", label: "Função" }, { id: "organ", label: "Órgão" }] },
  ] };
  it("não herda calendário, grupo ou dimensão de outra lente", () => {
    const state = readFederalState(new URLSearchParams("period=2025&group=recipient&filter=cnae_section:A&page=101"), federal, "C");
    expect(state).toMatchObject({ period: "2023M01", group: "function", page: 1, filters: [] });
    expect(availablePeriods(federal, "B")).toEqual(["2024", "2024M01"]);
  });
  it("recompõe cruzamentos da URL com uma categoria por dimensão", () => {
    const state = readFederalState(new URLSearchParams("group=organ&filter=function:10&filter=organ:123&filter=function:12&filter=organ:&page=2"), federal, "C");
    expect(state.filters).toEqual(["function:12", "organ:123"]);
    expect(state.page).toBe(2);
  });
  it("não oferece subdivisão territorial abaixo do município", () => {
    expect(readFederalState(new URLSearchParams("group=territory&geography=municipio:2507507"), federal, "B").group).toBe("recipient");
  });
  it("volta à lente B e aos cruzamentos ao sair de uma ficha", () => {
    const href = safePanelHref(panelHref(new URLSearchParams("lens=B&group=organ&filter=organ:123&filter=recipient_class:empresa&period=2024M01")));
    const query = new URL(href, "https://portal.invalid").searchParams;
    expect(query.get("lens")).toBe("B");
    expect(query.getAll("filter")).toEqual(["organ:123", "recipient_class:empresa"]);
  });
});
