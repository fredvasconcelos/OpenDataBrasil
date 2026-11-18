import type { Dataset, Source } from "./types";

export interface InstitutionSources {
  id: string;
  name: string;
  acronym: string | null;
  url: string | null;
  datasets: number;
  sources: { id: string; name: string; url: string; datasets: number }[];
}

/**
 * Agrupa as fontes do catálogo por instituição, contando os conjuntos de dados habilitados.
 * Fontes sem conjunto habilitado ficam de fora: cadastro não é dado disponível no portal.
 * Ordem: instituições e fontes com mais conjuntos primeiro; empate pelo nome.
 */
export function groupInstitutions(sources: Source[], datasets: Dataset[]): InstitutionSources[] {
  const count = new Map<string, number>();
  for (const d of datasets) count.set(d.source_id, (count.get(d.source_id) ?? 0) + 1);
  const byInst = new Map<string, InstitutionSources>();
  for (const s of sources) {
    const n = count.get(s.source_id) ?? 0;
    if (!n) continue;
    const inst =
      byInst.get(s.institution_id) ??
      byInst
        .set(s.institution_id, {
          id: s.institution_id,
          name: s.institution_name ?? s.institution_id,
          acronym: s.institution_acronym ?? null,
          url: s.institution_url ?? null,
          datasets: 0,
          sources: [],
        })
        .get(s.institution_id)!;
    inst.datasets += n;
    inst.sources.push({ id: s.source_id, name: s.name, url: s.documentation_url ?? s.base_url, datasets: n });
  }
  const order = <T extends { datasets: number; name: string }>(a: T, b: T) =>
    b.datasets - a.datasets || a.name.localeCompare(b.name, "pt-BR");
  const out = [...byInst.values()].sort(order);
  out.forEach((i) => i.sources.sort(order));
  return out;
}
