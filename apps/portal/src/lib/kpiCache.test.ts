import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { flatten, matchKpi } from "./catalog";
import { indexFixture, navFixture } from "./fixtures";
import { KpiCache } from "./kpiCache";
import { allKpis, readState, resolveKpiId } from "./state";
import { validFocus } from "./zoom";

afterEach(() => vi.restoreAllMocks());

describe("índice leve e metadados do KPI", () => {
  const kpis = allKpis(navFixture);

  it("preserva o primeiro KPI e a normalização dos filtros sem a navegação completa", () => {
    for (const query of ["", "kpi=inexistente", "kpi=populacao_residente&nivel=uf&dim=c86,c2&periodo=2022", "kpi=doenca_cronica&nivel=municipio&dim=erro"]) {
      const params = new URLSearchParams(query);
      const id = resolveKpiId(params, indexFixture);
      const kpi = kpis.find((k) => k.kpi_id === id)!;
      expect(readState(params, indexFixture, kpi)).toEqual(readState(params, navFixture));
    }
    expect(resolveKpiId(new URLSearchParams(), indexFixture)).toBe(kpis[0]!.kpi_id);
  });

  it("mantém busca por nome, descrição e tabela usando só os campos do índice", () => {
    const full = flatten(navFixture);
    const light = flatten(indexFixture);
    for (const query of ["população", "fundo de participacao", "6579", "tabela 9606", "crônica"]) {
      expect(light.map((item) => matchKpi(item, query))).toEqual(full.map((item) => matchKpi(item, query)));
    }
  });

  it("reutiliza a pré-busca e isola os metadados por release", async () => {
    const initial = kpis[0]!;
    const second = kpis[1]!;
    const load = vi.spyOn(api, "kpi").mockResolvedValue(second);
    const cache = new KpiCache("release-1", initial);
    expect(await cache.get(initial.kpi_id)).toBe(initial);
    expect(load).not.toHaveBeenCalled();
    cache.preload(second.kpi_id);
    expect(await cache.get(second.kpi_id)).toBe(second);
    expect(load).toHaveBeenCalledExactlyOnceWith(second.kpi_id, "release-1");
    const changed = new KpiCache("release-2", null);
    await changed.get(second.kpi_id);
    expect(load).toHaveBeenLastCalledWith(second.kpi_id, "release-2");
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("permite nova tentativa após erro de carregamento", async () => {
    const second = kpis[1]!;
    const load = vi.spyOn(api, "kpi").mockRejectedValueOnce(new Error("indisponível")).mockResolvedValueOnce(second);
    const cache = new KpiCache("release-1", null);
    await expect(cache.get(second.kpi_id)).rejects.toThrow("indisponível");
    expect(await cache.get(second.kpi_id)).toBe(second);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("preserva o recorte por UF quando o KPI só publica Brasil e municípios", () => {
    const kpi = { ...kpis[0]!, levels: ["brasil", "municipio"], map_levels: ["brasil", "municipio"] };
    expect(validFocus(["municipio"], "uf:35", "municipio")).toBe(true);
    expect(validFocus(["municipio"], "uf:35", "uf")).toBe(false);
    const state = readState(new URLSearchParams(`kpi=${kpi.kpi_id}&nivel=municipio&foco=uf:35`), indexFixture, kpi);
    expect(state.focus).toBe("uf:35");
    expect(state.level).toBe("municipio");
  });
});
