import { afterEach, expect, it, vi } from "vitest";

import type { ContasTable } from "@/lib/contas/types";
import { contasApi } from "./contas";

afterEach(() => vi.restoreAllMocks());

const page = (keys: string[], release = "release-a"): ContasTable => ({
  lens: "A", geography_key: "brasil:1", group_by: "function", filters: [], sort: "value",
  page: 1, page_size: 10, pages: 2, rows_total: 2, value_total: 30, page_value: 20, notes: [],
  rows: keys.map((key) => ({ key, label: key, value: 20, share: 0.5, recipient: null })),
  provenance: { release_id: release, tables: [], periods: ["2025M01"], partial: false, period_notes: [] },
});

it("não perde áreas que estejam nas próximas páginas", async () => {
  const table = vi.spyOn(contasApi, "table").mockResolvedValueOnce(page(["10"])).mockResolvedValueOnce(page(["12"]));
  expect((await contasApi.areas("brasil:1", ["2025"])).rows.map((r) => r.key)).toEqual(["10", "12"]);
  expect(table).toHaveBeenLastCalledWith({ geography_key: "brasil:1", periods: ["2025"], group_by: "function", page: 2 });
});

it("não combina áreas de releases diferentes", async () => {
  vi.spyOn(contasApi, "table").mockResolvedValueOnce(page(["10"])).mockResolvedValueOnce(page(["12"], "release-b"));
  await expect(contasApi.areas("brasil:1", ["2025"])).rejects.toThrow("release_changed");
});

it("não apresenta lista incompleta quando uma página repete categorias", async () => {
  vi.spyOn(contasApi, "table").mockResolvedValueOnce(page(["10"])).mockResolvedValueOnce(page(["10"]));
  await expect(contasApi.areas("brasil:1", ["2025"])).rejects.toThrow("incomplete_areas");
});


it("envia lente B e os filtros sem convertê-los para transferências", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({})));
  await contasApi.table({ lens: "B", geography_key: "municipio:2507507", periods: ["2025"], group_by: "organ", filter: ["recipient_class:empresa"] });
  const query = new URL(String(fetcher.mock.calls[0]![0]), "http://portal").searchParams;
  expect(query.get("lens")).toBe("B");
  expect(query.get("geography_key")).toBe("municipio:2507507");
  expect(query.getAll("filter")).toEqual(["recipient_class:empresa"]);
});

it("consulta fases da execução sem enviar território nem somar fases", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({})));
  await contasApi.execution({ periods: ["2025"], dimension: "organ", filter: ["function:10", "organ:123"], page: 2 });
  const url = new URL(String(fetcher.mock.calls[0]![0]), "http://portal");
  expect(url.pathname).toMatch(/contas\/execucao$/);
  expect(url.searchParams.getAll("filter")).toEqual(["function:10", "organ:123"]);
  expect(url.searchParams.has("geography_key")).toBe(false);
});
