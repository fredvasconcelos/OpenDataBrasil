"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ChevronLeftIcon, CloseIcon, CoverageIcon, InfoIcon, SwapIcon } from "@/components/icons";
import { formatPeriod, formatShare, formatValue, unitShort } from "@/lib/format";
import { compositionBases, percentageDimension, type SharePolicies } from "@/lib/categoryShares";
import type { Kpi, Pivot } from "@/lib/types";

// Tabela dinâmica (B6, DS 2.8; única tabela do painel desde o DS 2.9): o usuário põe
// Território, Período e as dimensões de "Detalhar por" nas linhas ou nas colunas, como no
// Excel. A API só reorganiza o que a Gold publica (ou deriva pela regra do KPI): campos
// fora da tabela ficam no Total, nada é somado no navegador e nada é acumulado (ADR-0026).
// DS 2.9: segue o Período da barra lateral; ordena pela coluna clicada; "Calcular % por"
// (Total das categorias, grupo, coluna ou total geral, só divisões entre valores
// publicados); clique na linha seleciona o território; botão i com as notas, que fica
// vermelho e abre sozinho quando um detalhe pedido não existe no recorte.

export interface PivotField {
  id: string;
  label: string;
}

interface ControlsProps {
  fields: PivotField[];
  rows: string[];
  cols: string[];
  onChange: (rows: string[], cols: string[]) => void;
}

export function PivotControls({ fields, rows, cols, onChange }: ControlsProps) {
  const t = useTranslations("pivot");
  const free = fields.filter((f) => !rows.includes(f.id) && !cols.includes(f.id));
  const label = (id: string) => fields.find((f) => f.id === id)?.label ?? id;
  const zone = (name: "rows" | "cols", list: string[], other: string[]) => (
    <div className="pivot-zone" role="group" aria-label={t(name)}>
      <span className="pivot-zone-label">{t(name)}</span>
      {list.map((id, i) => (
        <span key={id} className="pivot-chip">
          {label(id)}
          {i > 0 ? (
            <button
              type="button"
              aria-label={t("moveUp", { field: label(id) })}
              onClick={() => {
                const next = [...list];
                [next[i - 1], next[i]] = [next[i]!, next[i - 1]!];
                onChange(name === "rows" ? next : other, name === "rows" ? other : next);
              }}
            >
              <ChevronLeftIcon />
            </button>
          ) : null}
          {list.length > 1 ? (
            <button
              type="button"
              aria-label={t("remove", { field: label(id) })}
              onClick={() => {
                const next = list.filter((x) => x !== id);
                onChange(name === "rows" ? next : other, name === "rows" ? other : next);
              }}
            >
              <CloseIcon size={14} />
            </button>
          ) : null}
        </span>
      ))}
      {free.length && list.length < 3 ? (
        <select
          aria-label={t("add", { zone: t(name) })}
          value=""
          onChange={(e) => {
            if (!e.target.value) return;
            const next = [...list, e.target.value];
            onChange(name === "rows" ? next : other, name === "rows" ? other : next);
          }}
        >
          <option value="">{t("addField")}</option>
          {free.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </select>
      ) : null}
    </div>
  );
  return (
    <div className="pivot-controls">
      {zone("rows", rows, cols)}
      {zone("cols", cols, rows)}
      <button type="button" className="pivot-swap" title={t("swap")} aria-label={t("swap")} onClick={() => onChange(cols, rows)}>
        <SwapIcon />
        <span aria-hidden="true">{t("swapShort")}</span>
      </button>
    </div>
  );
}

/** Base do % (DS 2.9): nenhuma, Total das categorias, grupo, coluna (rodapé) ou total geral. */
export type PivotShare = "none" | "total" | "parent" | "column" | "overall";

type Cell = Pivot["cells"][number][number];
const SEP = "\u0001";
const key = (rk: readonly string[], ck: readonly string[]) => `${rk.join(SEP)}\u0002${ck.join(SEP)}`;

/**
 * Chaves do denominador de uma célula: as dimensões trocadas pelo Total (todas, em
 * "total"; só a última detalhada, em "parent"). null quando a célula já é o Total.
 */
export function shareKeys(
  base: "total" | "parent",
  rowFields: readonly string[],
  colFields: readonly string[],
  rk: readonly string[],
  ck: readonly string[],
  totals: Readonly<Record<string, string>>,
): [string[], string[]] | null {
  const slots = [...rowFields.map((f, i) => ["r", i, f] as const), ...colFields.map((f, i) => ["c", i, f] as const)];
  const r = [...rk];
  const c = [...ck];
  const detailed = slots.filter(([side, i, f]) => totals[f] && (side === "r" ? rk[i] : ck[i]) !== totals[f]);
  if (!detailed.length) return null;
  for (const [side, i, f] of base === "total" ? detailed : detailed.slice(-1)) {
    if (side === "r") r[i] = totals[f]!;
    else c[i] = totals[f]!;
  }
  return [r, c];
}

/** Bases de % disponíveis para a tabela: depende das dimensões presentes e do rodapé. */
export function shareBases(data: Pivot, totals: Readonly<Record<string, string>>): PivotShare[] {
  const dims = [...data.row_fields, ...data.col_fields].filter((f) => totals[f.id]).length;
  return [
    "none",
    ...(dims ? (["total"] as const) : []),
    ...(dims > 1 ? (["parent"] as const) : []),
    ...(data.footer ? (["column", "overall"] as const) : []),
  ];
}

interface Props {
  data: Pivot;
  /** Classificação → chave da categoria Total (dimensões do KPI). */
  totals: Record<string, string>;
  /** KPI aditivo e fora de "%": o % das partes faz sentido (DS 2.3.6). */
  shares: boolean;
  selected: string | null;
  onSelect: (geography: string) => void;
  /** Links oficiais já publicados no catálogo, para os diagnósticos da API. */
  sources?: Kpi["source"]["tables"];
  /** Notas extras para a janela de informação (ex.: acumulado fica no mapa e no gráfico). */
  notes?: string[];
  sharePolicies?: SharePolicies;
  dimensionOrder?: readonly string[];
  /** Controles de Linhas/Colunas, na mesma faixa de "Calcular % por" (DS 2.17). */
  controls?: ReactNode;
}

/**
 * Níveis do cabeçalho de colunas que aparecem (DS 2.17). Período com um só valor sai do
 * cabeçalho: já está no título da tabela ("Dados · Região · 2022") e, com três campos
 * nas colunas, a linha repetida tirava o espaço das linhas de dados. O último nível
 * (com a ordenação) fica sempre.
 */
export function visibleColumnLevels(data: Pick<Pivot, "col_fields" | "columns">): number[] {
  const nc = data.col_fields.length;
  return data.col_fields
    .map((_, level) => level)
    .filter((level) => level === nc - 1 || data.col_fields[level]?.id !== "periodo"
      || new Set(data.columns.map((c) => c.labels[level])).size > 1);
}

/** Sequências de colunas com o mesmo grupo até o nível dado (para o colSpan do cabeçalho). */
export function columnGroups(columns: Pivot["columns"], level: number): { start: number; span: number; label: string }[] {
  const out: { start: number; span: number; label: string; key: string }[] = [];
  columns.forEach((c, j) => {
    const k = c.keys.slice(0, level + 1).join(SEP);
    const last = out[out.length - 1];
    if (last && last.key === k) last.span += 1;
    else out.push({ start: j, span: 1, label: c.labels[level] ?? "", key: k });
  });
  return out.map(({ start, span, label }) => ({ start, span, label }));
}

export function PivotTable({ data, totals, shares, selected, onSelect, sources = [], notes = [], sharePolicies = {}, dimensionOrder, controls }: Props) {
  const t = useTranslations("pivot");
  const tt = useTranslations("table");
  const tl = useTranslations("levels");
  const unit = data.provenance.price_base
    ? `${unitShort(data.unit)} de ${data.provenance.price_base}`
    : unitShort(data.unit);
  const nr = data.row_fields.length;
  const nc = data.col_fields.length;
  const levels = visibleColumnLevels(data);
  // Primeira coluna de cada grupo visível de cima: recebe o fio de separação.
  const groupStart = new Set(levels.length > 1 ? columnGroups(data.columns, levels[levels.length - 2]!).map((g) => g.start).filter((j) => j > 0) : []);
  const rowIds = data.row_fields.map((f) => f.id);
  const colIds = data.col_fields.map((f) => f.id);
  const byTerritory = rowIds[0] === "territorio";
  // A API decide disponibilidade e precedência; o portal só traduz os códigos.
  const allAlerts = data.alerts ?? [];
  const severity = allAlerts.some((a) => a.severity === "danger") ? "danger" : allAlerts.length ? "warning" : null;
  const alertText = (alert: (typeof allAlerts)[number]) => {
    const p = alert.params;
    const field = [...data.row_fields, ...data.col_fields].find((f) => f.id === p.dimension);
    const list = (values: readonly string[] = []) => values.map(formatPeriod).join(", ");
    const code = alert.code === "A3" && p.reference === "published_total" ? "A3Territories" : alert.code;
    return t(`coverage.${code}`, {
      level: tl(p.level), dimension: field?.label ?? p.dimension ?? "",
      periods: list(p.periods), available: list(p.available_periods),
      levels: (p.available_levels ?? []).map((l) => tl(l)).join(", "),
      observed: p.observed ?? 0, expected: p.expected ?? 0,
      dimensions: (p.dimensions ?? []).map((id) => [...data.row_fields, ...data.col_fields].find((f) => f.id === id)?.label ?? id).join(", "),
    });
  };

  const values = new Map<string, number | null>();
  data.rows.forEach((r, i) => data.columns.forEach((c, j) => values.set(key(r.keys, c.keys), data.cells[i]?.[j]?.value ?? null)));

  // A composição é separada das bases publicadas e nunca substitui o Total oficial.
  const hierarchy = dimensionOrder ?? [...rowIds, ...colIds].filter((id) => totals[id]);
  const activeDimensions = hierarchy.filter((id) => totals[id] && [...rowIds, ...colIds].includes(id));
  const normalized = activeDimensions.some((id) => sharePolicies[id] === "displayed_sum");
  const grouped = activeDimensions.some((id) => sharePolicies[id] === "published_group");
  const comparative = normalized || grouped;
  const categoryShares = shares || activeDimensions.some((id) => sharePolicies[id] === "published_total");
  const bases: PivotShare[] = comparative
    ? ["none", ...(activeDimensions.length > 1 ? ["parent" as const] : activeDimensions.length ? ["total" as const] : [])]
    : categoryShares ? shareBases(data, totals).filter((b) => shares || (b !== "column" && b !== "overall")) : ["none"];
  const compositions = compositionBases(data, totals, sharePolicies);
  const publishedBases = new Map<string, Map<string, number | null>>();
  for (const item of data.share_bases ?? []) {
    const values = publishedBases.get(item.classification_id) ?? new Map<string, number | null>();
    values.set(key(item.row_keys, item.column_keys), item.value);
    publishedBases.set(item.classification_id, values);
  }
  const [chosen, setChosen] = useState<PivotShare | null>(null);
  const base: PivotShare = chosen && bases.includes(chosen) ? chosen : bases.includes("parent") ? "parent" : bases.includes("total") ? "total" : "none";
  const footerAt = (ck: readonly string[]) => {
    const j = data.columns.findIndex((c) => c.keys.join(SEP) === ck.join(SEP));
    return j < 0 ? null : (data.footer_cells?.[j]?.value ?? null);
  };
  const denominator = (rk: readonly string[], ck: readonly string[], j: number): number | null => {
    if (base === "none") return null;
    if (base === "column") return data.footer_cells?.[j]?.value ?? null;
    if (base === "overall") {
      const tk = shareKeys("total", [], colIds, [], ck, totals);
      return footerAt(tk ? tk[1] : ck);
    }
    const dimension = percentageDimension(rowIds, colIds, rk, ck, totals, hierarchy);
    if (dimension && sharePolicies[dimension] === "none") return null;
    if (dimension && (sharePolicies[dimension] === "displayed_sum" || sharePolicies[dimension] === "published_group")) {
      const r = [...rk];
      const c = [...ck];
      const ri = rowIds.indexOf(dimension);
      const ci = colIds.indexOf(dimension);
      if (ri >= 0) r[ri] = totals[dimension]!;
      if (ci >= 0) c[ci] = totals[dimension]!;
      return (sharePolicies[dimension] === "published_group" ? publishedBases : compositions)
        .get(dimension)?.get(key(r, c)) ?? null;
    }
    if (base === "parent" && dimension) {
      const r = [...rk];
      const c = [...ck];
      const ri = rowIds.indexOf(dimension);
      const ci = colIds.indexOf(dimension);
      if (ri >= 0) r[ri] = totals[dimension]!;
      if (ci >= 0) c[ci] = totals[dimension]!;
      return values.get(key(r, c)) ?? null;
    }
    const sk = shareKeys(base, rowIds, colIds, rk, ck, totals);
    return values.get(sk ? key(sk[0], sk[1]) : key(rk, ck)) ?? null;
  };

  // Ordenação: pela coluna clicada (maior primeiro) ou na ordem da API (rótulos).
  // Padrão com Território nas linhas: o Total do último período, como no mapa.
  const shape = `${rowIds.join()}|${colIds.join()}|${data.columns.length}`;
  const mainCol = (() => {
    if (!byTerritory) return null;
    const totalsOnly = data.columns
      .map((c, j) => ({ c, j }))
      .filter(({ c }) => colIds.every((f, i) => !totals[f] || c.keys[i] === totals[f]));
    return (totalsOnly.at(-1) ?? { j: data.columns.length - 1 }).j;
  })();
  const [sortState, setSortState] = useState<{ shape: string; by: number | null; desc: boolean } | null>(null);
  const sort = sortState?.shape === shape ? sortState : { shape, by: mainCol, desc: true };
  const order = data.rows.map((_, i) => i);
  if (sort.by !== null) {
    const col = sort.by;
    const v = (i: number) => data.cells[i]?.[col]?.value ?? null;
    order.sort((a, b) => {
      const va = v(a);
      const vb = v(b);
      if (va === null && vb === null) return a - b;
      if (va === null) return 1;
      if (vb === null) return -1;
      return sort.desc ? vb - va : va - vb;
    });
  }
  const sortBy = (by: number | null) =>
    setSortState({ shape, by, desc: sort.by === by ? !sort.desc : true });

  // Só um novo diagnóstico vermelho abre a janela automaticamente (ADR-0040).
  const [info, setInfo] = useState(false);
  const alertKey = JSON.stringify(allAlerts.filter((a) => a.severity === "danger"));
  const [seenAlert, setSeenAlert] = useState("");
  if (alertKey !== seenAlert) {
    setSeenAlert(alertKey);
    if (alertKey !== "[]") setInfo(true);
  }

  // A linha selecionada (território clicado no mapa) fica à vista dentro do quadro.
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = wrap.current;
    if (!box || !selected || !byTerritory) return;
    const row = Array.from(box.querySelectorAll<HTMLTableRowElement>("tbody tr")).find((tr) => tr.dataset.key === selected);
    if (!row) return;
    const header = box.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    const b = box.getBoundingClientRect();
    const r = row.getBoundingClientRect();
    if (r.top >= b.top + header && r.bottom <= b.top + box.clientHeight) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const top = box.scrollTop + (r.top - b.top) - header - (box.clientHeight - header - r.height) / 2;
    box.scrollTo?.({ top: Math.max(0, top), behavior: reduce ? "auto" : "smooth" });
  }, [selected, data, byTerritory]);

  const show = (cell: Cell | undefined, rk: readonly string[], ck: readonly string[], j: number) => {
    const d = cell?.value != null ? denominator(rk, ck, j) : null;
    const share = d && cell?.value != null ? (cell.value / d) * 100 : null;
    const dimension = percentageDimension(rowIds, colIds, rk, ck, totals, hierarchy);
    const totalComposition = dimension && (sharePolicies[dimension] === "displayed_sum" || sharePolicies[dimension] === "published_group") &&
      [...rowIds.map((id, i) => [id, rk[i]]), ...colIds.map((id, i) => [id, ck[i]])]
        .every(([id, value]) => !totals[id!] || value === totals[id!]);
    return (
      <>
        <span className="cell-value">{cell ? formatValue(cell.value, cell.status) : formatValue(null, "absent")}</span>
        {totalComposition && d ? <span className="cell-share-base">{tt(sharePolicies[dimension!] === "published_group" ? "groupBase" : "compositionBase", { value: formatValue(d) })} ({formatShare(100)})</span> :
          share !== null ? <span className="share"> ({formatShare(share)})</span> : null}
      </>
    );
  };
  // Linha de totais: o % é sobre ela mesma (Total das categorias, grupo ou total geral).
  const showFooter = (cell: Cell | undefined, ck: readonly string[]) => {
    const sk = base === "total" || base === "parent" ? shareKeys(base, [], colIds, [], ck, totals) : null;
    const d = comparative ? null :
      base === "column"
        ? (cell?.value ?? null) // a própria linha de totais é 100% da coluna
        : base === "overall"
          ? footerAt(shareKeys("total", [], colIds, [], ck, totals)?.[1] ?? ck)
          : sk
            ? footerAt(sk[1])
            : null;
    const share = d && cell?.value != null ? (cell.value / d) * 100 : null;
    return (
      <>
        <span className="cell-value">{cell ? formatValue(cell.value, cell.status) : formatValue(null, "absent")}</span>
        {share !== null ? <span className="share"> ({formatShare(share)})</span> : null}
      </>
    );
  };
  const arrow = (j: number | null) => (sort.by === j ? (j === null ? "" : sort.desc ? " ↓" : " ↑") : "");
  const ariaSort = (j: number | null) => (sort.by === j && j !== null ? (sort.desc ? "descending" : "ascending") : undefined);
  const blank = sort.by === null; // rótulos repetidos em branco só na ordem da API (agrupamento)
  const shareLabel = (b: PivotShare) =>
    b === "column" || b === "overall" ? t(`share.${b}`, { name: data.footer?.labels[0] ?? "" }) : t(`share.${b}`);

  return (
    <div className="table-box">
      {normalized ? <p className="composition-note">{tt("compositionNote")}</p> : null}
      {grouped ? <p className="composition-note">{tt("groupBaseNote")}</p> : null}
      <div className="pivot-toolbar">
      {controls}
      <div className="share-base">
        {bases.length > 1 ? (
          <label>
            {tt("shareOf")}
            <select value={base} onChange={(e) => setChosen(e.target.value as PivotShare)}>
              {bases.map((b) => (
                <option key={b} value={b}>
                  {shareLabel(b)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <span className="pivot-unit">{tt("unitShort", { unit: base !== "none" ? `${unit} (%)` : unit })}</span>
        <button
          type="button"
          className={`info-button${severity ? ` is-${severity}` : ""}`}
          aria-expanded={info}
          aria-controls="table-info"
          aria-label={severity ? t(`coverage.button.${severity}`) : tt("about")}
          title={severity ? t(`coverage.button.${severity}`) : tt("about")}
          onClick={() => setInfo((v) => !v)}
        >
          {severity ? <CoverageIcon severity={severity} /> : <InfoIcon />}
        </button>
        {info ? (
          <div id="table-info" className="table-info caption" role="note">
            {(["danger", "warning"] as const).map((kind) => allAlerts.some((a) => a.severity === kind) ? (
              <div key={kind} className={`table-alert is-${kind}`} role={kind === "danger" ? "alert" : "status"}>
                <strong>{t(`coverage.title.${kind}`)}</strong>
                <ul>
                  {allAlerts.filter((a) => a.severity === kind).map((a) => (
                    <li key={JSON.stringify(a)}>{alertText(a)}{a.params.tables?.length ? <> {t("coverage.sources")} {a.params.tables.map((id, index) => {
                      const url = sources.find((s) => s.table_id === id)?.reference_url;
                      return <span key={id}>{index ? ", " : ""}{url ? <a href={url} target="_blank" rel="noreferrer">{id}</a> : id}</span>;
                    })}.</> : null}</li>
                  ))}
                </ul>
              </div>
            ) : null)}
            <p>
              <strong>{tt("aboutUnit")}</strong> {unit}.
            </p>
            <p>{t("note")}</p>
            {base !== "none" ? <p>{t(`shareNote.${base}`)}</p> : null}
            {notes.map((n) => (
              <p key={n}>{n}</p>
            ))}
            {data.footer ? <p>{tt("aboutFooter", { name: data.footer.labels[0] ?? "" })}</p> : null}
          </div>
        ) : null}
      </div>
      </div>
      <div className="table-wrap pivot-wrap" ref={wrap}>
        <table className="data-table pivot-table">
          <caption className="sr-only">{t("caption", { rows: data.rows.length, cols: data.columns.length })}</caption>
          <thead>
            {levels.map((level) => (
              <tr key={data.col_fields[level]!.id}>
                {level === nc - 1 ? (
                  data.row_fields.map((rf, k) => (
                    <th scope="col" key={rf.id} className="pivot-corner" aria-sort={k === 0 && sort.by === null ? "ascending" : undefined}>
                      {k === 0 ? (
                        <button type="button" onClick={() => sortBy(null)} aria-label={t("sortByLabel", { field: rf.label })}>
                          {rf.label}
                        </button>
                      ) : (
                        rf.label
                      )}
                    </th>
                  ))
                ) : (
                  <th colSpan={nr} className="pivot-corner" aria-hidden="true" />
                )}
                {level < nc - 1
                  ? // Grupos (DS 2.17): uma célula por sequência de colunas com o mesmo grupo
                    // em todos os níveis de cima, cobrindo as colunas que agrupa.
                    columnGroups(data.columns, level).map((g) => (
                      <th scope="colgroup" key={`${level}-${g.start}`} colSpan={g.span} className="pivot-group">
                        {g.label}
                      </th>
                    ))
                  : data.columns.map((c, j) => (
                      <th scope="col" key={`${level}-${c.keys.join("|")}`} aria-sort={ariaSort(j)} className={groupStart.has(j) ? "pivot-start" : undefined}>
                        <button type="button" onClick={() => sortBy(j)} aria-label={t("sortByColumn", { column: c.labels.join(" · ") })}>
                          {c.labels[level]}
                          {arrow(j)}
                        </button>
                      </th>
                    ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {order.map((i, pos) => {
              const r = data.rows[i]!;
              const prev = pos > 0 ? data.rows[order[pos - 1]!] : undefined;
              const geo = byTerritory ? r.keys[0] : undefined;
              return (
                <tr
                  key={r.keys.join("|")}
                  data-key={geo}
                  aria-selected={geo !== undefined ? selected === geo : undefined}
                  onClick={geo ? () => onSelect(geo) : undefined}
                  className={geo ? "is-selectable" : undefined}
                >
                  {r.labels.map((l, k) => (
                    <th scope="row" key={k}>
                      {blank && k < nr - 1 && prev?.labels[k] === l ? "" : l}
                    </th>
                  ))}
                  {data.columns.map((c, j) => (
                    <td key={j} className={groupStart.has(j) ? "num pivot-start" : "num"}>
                      {show(data.cells[i]?.[j], r.keys, c.keys, j)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
          {data.footer ? (
            <tfoot>
              <tr>
                <th scope="row">{tt("footer", { name: data.footer.labels[0] ?? "" })}</th>
                {data.columns.map((c, j) => (
                  <td key={j} className={groupStart.has(j) ? "num pivot-start" : "num"}>
                    {showFooter(data.footer_cells?.[j] ?? undefined, c.keys)}
                  </td>
                ))}
              </tr>
            </tfoot>
          ) : null}
        </table>
      </div>
    </div>
  );
}
