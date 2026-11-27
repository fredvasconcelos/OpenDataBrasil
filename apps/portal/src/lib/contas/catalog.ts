// Uma definição de catálogo para o Início e a barra lateral (guia DS, seção 12).
import { contasApi } from "@/lib/api/contas";
import { defaultPeriod } from "@/lib/contas/state";
import type { ContasMeta } from "@/lib/contas/types";
import { FA, type FaDef } from "@/lib/faIcons";
import { normalize, type ThemeFamily } from "@/lib/themes";

const PANEL = "/contas/painel";
// Os mesmos nomes dos cartões do painel; um tipo novo da fonte aparece com o rótulo da API.
const TYPE_LABELS: Record<string, "constitutional" | "legal"> = {
  "Constitucionais e Royalties": "constitutional",
  "Legais, Voluntárias e Específicas": "legal",
};

export interface Item {
  id: string;
  label: string;
  href: string;
  /** Termos extras da busca (siglas e nomes populares), nunca exibidos. */
  terms?: string;
}

export interface Group {
  id: "visao" | "tipos" | "areas" | "recebimentos" | "execucao";
  label: string;
  note: string;
  icon: FaDef;
  family: ThemeFamily;
  terms: string;
  items: Item[];
}


type Text = (key: string, values?: Record<string, string | number>) => string;

export async function loadContasCatalog(meta?: ContasMeta) {
  const current = meta ?? await contasApi.meta();
  const period = defaultPeriod(current);
  const [areas, types] = await Promise.all([
    contasApi.areas("brasil:1", [period]),
    contasApi.table({ geography_key: "brasil:1", periods: [period], group_by: "transfer_type" }),
  ]);
  if ([areas, types].some((item) => item.provenance.release_id !== current.release_id)) throw new Error("release_changed");
  return { meta: current, period, areas: areas.rows, types: types.rows };
}

export type ContasCatalogData = Awaited<ReturnType<typeof loadContasCatalog>>;

export function contasGroups(data: ContasCatalogData | null, t: Text): Group[] {
  const c: Text = (key, values) => t(`contas.catalog.${key}`, values);
  const has = (lens: string) => data?.meta.lenses.some((item) => item.lens === lens && item.periods.length > 0);
  const groups: Group[] = data
    ? [
        {
          id: "visao",
          label: c("groups.visao.name"),
          note: c("groups.visao.note"),
          icon: FA.contas,
          family: "azul",
          terms: c("groups.visao.terms"),
          items: [
            { id: "total", label: c("items.total"), href: PANEL },
            { id: "onde", label: c("items.onde"), href: `${PANEL}#onde`, terms: c("items.ondeTerms") },
            { id: "quando", label: c("items.quando"), href: `${PANEL}#quando` },
            { id: "quem", label: c("items.quem"), href: `${PANEL}#quem`, terms: c("items.quemTerms") },
          ],
        },
        {
          id: "tipos",
          label: c("groups.tipos.name"),
          note: c("groups.tipos.note"),
          icon: FA.transferidos,
          family: "petroleo",
          terms: c("groups.tipos.terms"),
          items: data.types.map((r) => ({ id: r.key, label: TYPE_LABELS[r.key] ? t(`contas.highlights.${TYPE_LABELS[r.key]}`) : r.label, href: `${PANEL}#como`, terms: TYPE_LABELS[r.key] ? c(`items.${TYPE_LABELS[r.key]}Terms`) : undefined })),
        },
        {
          id: "areas",
          label: c("groups.areas.name"),
          note: c("groups.areas.note", { year: data.period.slice(0, 4) }),
          icon: FA.gestao,
          family: "roxo",
          terms: c("groups.areas.terms"),
          items: data.areas.map((r) => ({ id: r.key, label: r.label, href: `${PANEL}?${new URLSearchParams({ area: r.key })}` })),
        },
        ...(has("B") ? [{
          id: "recebimentos", label: c("groups.recebimentos.name"), note: c("groups.recebimentos.note"),
          icon: FA.recebimento, family: "verde", terms: c("groups.recebimentos.terms"),
          items: [
            { id: "pagamentos", label: c("items.receivedTotal"), href: `${PANEL}?lens=B` },
            { id: "mapa", label: c("items.receivedSeat"), href: `${PANEL}?lens=B#federal-map` },
            { id: "evolucao", label: c("items.receivedSeries"), href: `${PANEL}?lens=B#federal-series` },
            { id: "busca", label: c("items.receivedSearch"), href: `${PANEL}?lens=B#federal-busca` },
          ],
        } satisfies Group] : []),
        ...(has("C") ? [{
          id: "execucao", label: c("groups.execucao.name"), note: c("groups.execucao.note"),
          icon: FA.execucao, family: "ocre", terms: c("groups.execucao.terms"),
          items: [
            ...["committed", "liquidated", "paid", "payables_registered", "payables_cancelled", "payables_paid"].map((phase) => ({ id: phase, label: t(`contas.federal.phases.${phase}`), href: `${PANEL}?lens=C#fase-${phase}` })),
            ...data.meta.lenses.find((lens) => lens.lens === "C")!.dimensions.filter((d) => d.id.startsWith("localizer")).map((d) => ({ id: d.id, label: d.label, href: `${PANEL}?lens=C&group=${d.id}#federal-table` })),
          ],
        } satisfies Group] : []),
      ]
    : [];

  return groups;
}

export function matchContas(group: Group, item: Item, query: string): boolean {
  const term = normalize(query.trim());
  return !term || normalize(`${item.label} ${item.terms ?? ""} ${group.label} ${group.terms}`).includes(term);
}
