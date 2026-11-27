import { expect, it } from "vitest";
import messages from "../../../messages/pt-BR.json";
import { contasGroups, matchContas, type ContasCatalogData } from "./catalog";

const text = (key: string) => {
  const value = key.split(".").reduce<unknown>((current, part) => (current as Record<string, unknown>)[part], messages);
  return typeof value === "string" ? value : key;
};
const data: ContasCatalogData = {
  period: "2025", areas: [], types: ["Constitucionais e Royalties", "Legais, Voluntárias e Específicas"].map((key) => ({ key, label: key, value: 1, share: 0.5, recipient: null })),
  meta: { release_id: "teste", notes: [], recipient_classes: {}, lenses: (["A", "B", "C"] as const).map((lens) => ({ lens, label: lens, description: "", notes: [], dimensions: lens === "C" ? [{ id: "localizer_uf", label: "UF do localizador orçamentário" }] : [], group_by: [], periods: ["2025M01"], latest_period: "2025M01", statuses: [] })) },
};

it("Início e barra lateral recebem os mesmos grupos, destinos e famílias distintos", () => {
  const groups = contasGroups(data, text);
  expect(groups.map((group) => group.id)).toEqual(["visao", "tipos", "areas", "recebimentos", "execucao"]);
  expect(new Set(groups.map((group) => group.family)).size).toBe(5);
  const receipts = groups.find((group) => group.id === "recebimentos")!;
  expect(receipts.items.map((item) => item.href)).toEqual(["/contas/painel?lens=B", "/contas/painel?lens=B#federal-map", "/contas/painel?lens=B#federal-series", "/contas/painel?lens=B#federal-busca"]);
  expect(groups.find((group) => group.id === "execucao")!.items.some((item) => item.href.includes("group=localizer_uf"))).toBe(true);
});

it("termo de uma fase e FPM não contaminam itens de outros grupos", () => {
  const groups = contasGroups(data, text);
  const find = (query: string) => groups.flatMap((group) => group.items.filter((item) => matchContas(group, item, query)).map((item) => [group.id, item.id]));
  expect(find("empenhado")).toEqual([["execucao", "committed"]]);
  expect(find("fpm")).toEqual([["tipos", "Constitucionais e Royalties"]]);
  expect(find("ipca")).toEqual([]);
});

it("não anuncia lente ou localizador ausente do release", () => {
  const onlyA = { ...data, meta: { ...data.meta, lenses: data.meta.lenses.filter((lens) => lens.lens === "A") } };
  expect(contasGroups(onlyA, text).map((group) => group.id)).toEqual(["visao", "tipos", "areas"]);
  const withoutLocation = { ...data, meta: { ...data.meta, lenses: data.meta.lenses.map((lens) => ({ ...lens, dimensions: [] })) } };
  expect(contasGroups(withoutLocation, text).find((group) => group.id === "execucao")!.items).toHaveLength(6);
});
