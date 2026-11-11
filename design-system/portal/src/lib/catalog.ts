// Catálogo de temas e indicadores (Início, Sobre os dados e busca da barra lateral).
// Funções puras sobre o retorno de /navigation: nada aqui inventa dado; o que a API não
// traz aparece como "—" na tela. Os indicadores "em preparação" vêm de `planned` em cada
// subtema (panorama, ADR-0010): têm nome, tabela SIDRA e pesquisa, mas ainda não têm dados.

import { formatPeriod, parsePeriods } from "@/lib/period";
import { normalize } from "@/lib/themes";
import type { Kpi, Navigation, Subtheme, Theme } from "@/lib/types";

export interface CatalogKpi {
  kpi: Kpi;
  theme: Theme;
  themeLabel: string;
  subthemeLabel: string;
}

export function flatten(nav: Navigation): CatalogKpi[] {
  return nav.themes.flatMap((theme) =>
    theme.subthemes.flatMap((sub) => sub.kpis.map((kpi) => ({ kpi, theme, themeLabel: theme.label, subthemeLabel: sub.label }))),
  );
}

export type PlannedKpi = Subtheme["planned"][number];

export interface CatalogPlanned {
  planned: PlannedKpi;
  theme: Theme;
  themeLabel: string;
  subthemeLabel: string;
}

export function flattenPlanned(nav: Navigation): CatalogPlanned[] {
  return nav.themes.flatMap((theme) =>
    theme.subthemes.flatMap((sub) =>
      sub.planned.map((planned) => ({ planned, theme, themeLabel: theme.label, subthemeLabel: sub.label })),
    ),
  );
}

/** Onde a busca encontrou o termo (para o trecho destacado na barra lateral). */
export type MatchField = "label" | "theme" | "subtheme" | "table" | "description" | "name";

/**
 * Busca sem acentos e sem maiúsculas no nome do indicador, no tema, no subtema, na
 * descrição e pelo número da tabela da fonte (só dígitos, 2 ou mais). Devolve o primeiro
 * campo encontrado, na ordem de relevância, ou null.
 */
export function matchKpi(item: CatalogKpi, query: string): MatchField | null {
  const q = normalize(query);
  if (!q) return "label";
  const digits = q.replace(/\D/g, "");
  if (normalize(item.kpi.label).includes(q)) return "label";
  if (normalize(item.themeLabel).includes(q)) return "theme";
  if (normalize(item.subthemeLabel).includes(q)) return "subtheme";
  if (digits.length > 1 && digits === q.replace(/\s|tabela/g, "") && item.kpi.source.source_table_id === digits) return "table";
  if (normalize(item.kpi.name).includes(q)) return "name";
  if (normalize(item.kpi.description).includes(q)) return "description";
  return null;
}

/** Busca nos indicadores em preparação: nome, tema, subtema e número da tabela. */
export function matchPlanned(item: CatalogPlanned, query: string): MatchField | null {
  const q = normalize(query);
  if (!q) return "label";
  const digits = q.replace(/\D/g, "");
  if (normalize(item.planned.label).includes(q)) return "label";
  if (normalize(item.themeLabel).includes(q)) return "theme";
  if (normalize(item.subthemeLabel).includes(q)) return "subtheme";
  if (digits.length > 1 && digits === q.replace(/\s|tabela/g, "") && item.planned.source_table_id === digits) return "table";
  return null;
}

/** Partes de um texto com o termo marcado (para <mark>), ignorando acentos. */
export function highlight(text: string, query: string): { text: string; hit: boolean }[] {
  const q = normalize(query);
  if (!q) return [{ text, hit: false }];
  // normalize() preserva o comprimento quando só remove diacríticos combinantes de letras latinas.
  const base = text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
  if (base.length !== text.length) return [{ text, hit: false }];
  const out: { text: string; hit: boolean }[] = [];
  let i = 0;
  let at = base.indexOf(q);
  while (at >= 0) {
    if (at > i) out.push({ text: text.slice(i, at), hit: false });
    out.push({ text: text.slice(at, at + q.length), hit: true });
    i = at + q.length;
    at = base.indexOf(q, i);
  }
  if (i < text.length) out.push({ text: text.slice(i), hit: false });
  return out;
}

/** Trecho curto em volta do termo (descrição), como na busca da barra lateral. */
export function snippet(text: string, query: string, before = 28, after = 40): string {
  const base = normalize(text);
  const at = base.indexOf(normalize(query));
  if (at < 0) return text.slice(0, before + after);
  const start = Math.max(0, at - before);
  const end = Math.min(text.length, at + query.trim().length + after);
  return `${start > 0 ? "…" : ""}${text.slice(start, end)}${end < text.length ? "…" : ""}`;
}

/** "2001–2026 (22)", "mar 2020–dez 2024 (58)", "2022" ou "—". */
export function periodRange(periods: readonly string[]): string {
  if (!periods.length) return "—";
  const parsed = parsePeriods(periods);
  const list = parsed ? parsed.map((p) => formatPeriod(p)) : [...periods].sort();
  if (list.length === 1) return list[0] as string;
  return `${list[0]}–${list[list.length - 1]} (${list.length})`;
}

/** Dimensão principal (1ª) e as demais, como no catálogo (ADR-0010). */
export function dimensionsText(kpi: Kpi): { main: string | null; others: string | null } {
  const [first, ...rest] = kpi.dimensions;
  return { main: first?.label ?? null, others: rest.length ? rest.map((d) => d.label).join("; ") : null };
}

export const plural = (n: number, one: string, many: string) => `${n.toLocaleString("pt-BR")} ${n === 1 ? one : many}`;
