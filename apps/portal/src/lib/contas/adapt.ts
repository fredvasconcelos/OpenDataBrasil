// Adaptadores: respostas da API das contas → formatos que MapView e SeriesChart já leem.
// Só mudam a forma; nenhum valor é somado, dividido ou estimado aqui (ADR-0039, seção 5).
import type { MapValue, Series } from "@/lib/types";

import type { ContasMap, ContasRanking, ContasSeries, ContasTable, PeriodStatus } from "./types";

/** Preserva os valores da tabela filtrada da API no componente de recebedores. */
export function toRanking(table: ContasTable, year: number): ContasRanking {
  return {
    lens: table.lens,
    geography_key: table.geography_key,
    year,
    page: table.page,
    page_size: table.page_size,
    pages: table.pages,
    total_recipients: table.rows_total,
    rows: table.rows.map((row, index) => {
      if (!row.recipient) throw new Error("recipient_unavailable");
      return { rank: (table.page - 1) * table.page_size + index + 1, recipient: row.recipient, value: row.value };
    }),
    notes: table.notes,
    provenance: table.provenance,
  };
}

/** Linhas do mapa das contas → valores do MapView. */
export function toMapValues(map: ContasMap): MapValue[] {
  return map.rows.map((r) => ({ geography_key: r.geography_key, name: r.name, value: r.value, status: "valid" }));
}

/**
 * Série das contas → Series do SeriesChart. O eixo já lê `AAAAMmm`. O mês aberto vira
 * `partial_period` (o SeriesChart e o tooltip marcam como parcial); os demais, `valid`.
 */
export function toSeries(series: ContasSeries, geographyName: string, category: string | null = null): Series {
  const open = new Set((series.provenance.period_notes ?? []).filter((n) => n.status === "aberto").map((n) => n.period));
  return {
    kpi_id: "contas_transferencias",
    indicator_id: `contas_${series.lens}`,
    geography: { geography_key: series.geography_key, name: geographyName, level_id: series.geography_key.split(":")[0] ?? "" },
    unit: "Reais",
    grain: series.grain === "mes" ? "mes" : "ano",
    // A rota pode devolver “Demais” junto da categoria pedida. Com filtro de área,
    // só a linha selecionada representa o contexto dos cartões e do mapa.
    series: series.lines.filter((line) => !category || line.category_code === category).map((l) => ({
      key: l.category_code,
      label: l.label,
      full_label: l.label,
      categories: {},
      depth: 0,
      points: l.points.map((p) => ({ period: p.period, value: p.value, status: open.has(p.period) ? "partial_period" : "valid" })),
    })),
    provenance: { release_id: series.provenance.release_id, tables: series.provenance.tables, derived: false, truncated: false },
  };
}

/** Valor de uma linha da série num período, como veio da API (null se não houver). */
export function pointAt(series: ContasSeries, categoryCode: string, period: string): number | null {
  const line = series.lines.find((l) => l.category_code === categoryCode);
  return line?.points.find((p) => p.period === period)?.value ?? null;
}

/** Notas de período que pedem aviso (aberto ou incompleto), na ordem do tempo. */
export function periodAlerts(notes: readonly PeriodStatus[] | undefined): PeriodStatus[] {
  return [...(notes ?? [])].filter((n) => n.status !== "fechado").sort((a, b) => a.period.localeCompare(b.period));
}
