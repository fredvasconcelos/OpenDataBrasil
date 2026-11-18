// Tabelas de origem de um indicador (DS 2.9). Um KPI pode juntar tabelas-irmãs da fonte
// (ADR-0018): no SIDRA, a 4487 traz o Total e o sexo, e a 4490 traz a cor ou raça, com a
// mesma variável. A API diz de que tabela vem cada detalhe (`source_table_ids`) e o que
// cada tabela traz (`source.tables`); aqui só se escolhe o que mostrar.
import type { Kpi } from "@/lib/types";

export interface SourceTableRef {
  id: string;
  url: string | null;
  /** O que a tabela traz neste uso: "Total" e/ou os detalhes (rótulos). */
  role: string[];
}

/**
 * Tabelas que sustentam o que está na tela: a principal (Total) e as dos detalhes
 * ativos, sem repetir. Sem detalhe vindo de outra tabela, só a principal.
 */
export function tablesInUse(kpi: Kpi, dimensions: readonly string[], totalLabel: string): SourceTableRef[] {
  const main = kpi.source.source_table_id;
  const url = (id: string) =>
    kpi.source.tables?.find((t) => t.table_id === id)?.reference_url ?? (id === main ? (kpi.source.reference_url ?? null) : null);
  const out: SourceTableRef[] = [{ id: main, url: url(main), role: [totalLabel] }];
  for (const d of kpi.dimensions ?? []) {
    if (!dimensions.includes(d.classification_id)) continue;
    for (const id of d.source_table_ids ?? []) {
      const found = out.find((t) => t.id === id);
      if (found) found.role.push(d.label);
      else out.push({ id, url: url(id), role: [d.label] });
    }
  }
  return out;
}

/** Todas as tabelas de origem, a principal primeiro, com o que cada uma traz. */
export function allSourceTables(kpi: Kpi, totalLabel: string): (SourceTableRef & { periods: string[] })[] {
  const main = kpi.source.source_table_id;
  const label = (cid: string) => (kpi.dimensions ?? []).find((d) => d.classification_id === cid)?.label ?? cid;
  return (kpi.source.tables ?? []).map((t) => ({
    id: t.table_id,
    url: t.reference_url ?? null,
    role: [...(t.table_id === main ? [totalLabel] : []), ...(t.classification_ids ?? []).map(label)],
    periods: t.periods ?? [],
  }));
}
