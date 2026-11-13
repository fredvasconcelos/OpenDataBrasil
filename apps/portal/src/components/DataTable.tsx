"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { formatShare, formatValue, unitShort } from "@/lib/format";
import type { Table } from "@/lib/types";

type Column = Table["columns"][number];
type Row = NonNullable<Table["footer"]>;

/** Base do % (DS 2.3.9): o território (linha), o grupo, a coluna (rodapé) ou o total geral. */
export type ShareBase = "row" | "group" | "column" | "overall";

/** Grupos com mais linhas internas que isto começam recolhidos (expansíveis no cabeçalho). */
export const COLLAPSE_AFTER = 12;

interface Group {
  head: Column;
  inner: Column[];
}

/** Colunas agrupadas pela categoria da primeira dimensão, na ordem da API. */
export function groupColumns(columns: readonly Column[]): Group[] {
  const groups = new Map<string, Group>();
  for (const c of columns) {
    const g = c.group ?? c.key;
    const found = groups.get(g);
    if (!found) groups.set(g, { head: c, inner: [] });
    else found.inner.push(c);
  }
  return [...groups.values()];
}

/** Rótulo dentro do grupo: "Branca › Homens" sob "Branca" vira "Homens". */
export function innerLabel(head: Column, c: Column): string {
  const prefix = `${head.label} › `;
  return c.label.startsWith(prefix) ? c.label.slice(prefix.length) : c.label;
}

/** Denominador do % de uma célula, pela base escolhida; null quando não se aplica. */
export function shareBase(
  base: ShareBase,
  c: Column,
  row: Row,
  footer: Row | null | undefined,
  totalKey: string,
): number | null {
  const value = (r: Row | null | undefined, key: string | null | undefined) =>
    key ? (r?.cells[key]?.value ?? null) : null;
  if (base === "column") return value(footer, c.key);
  if (base === "overall") return value(footer, totalKey);
  if (c.key === totalKey) return null; // o Total é 100% da linha e do grupo
  if (base === "group") return value(row, c.parent ?? totalKey);
  return value(row, totalKey);
}


interface Props {
  data: Table;
  /** KPI aditivo: as categorias mostram também o % do Total (DS 2.3.6). */
  additive?: boolean;
  selected: string | null;
  sort: "value" | "name";
  order: "asc" | "desc";
  onSort: (sort: "value" | "name") => void;
  onPage: (offset: number) => void;
  onSelect: (key: string) => void;
}

export function DataTable({ data, additive = false, selected, sort, order, onSort, onPage, onSelect }: Props) {
  const t = useTranslations("table");
  // Unidade embaixo do nome de cada coluna: "pessoas", "R$ de jan/2018" (DS 2.3.6).
  const unit = data.provenance.price_base
    ? `${unitShort(data.unit)} de ${data.provenance.price_base}`
    : unitShort(data.unit);
  const totalKey = data.columns[0]?.key ?? "total";
  const groups = groupColumns(data.columns);
  const nested = groups.some((g) => g.inner.length > 0);
  const footer = data.footer ?? null;
  // % só em KPIs aditivos (a soma das partes é o todo) e fora de unidades que já são %.
  const shares = additive && unitShort(data.unit) !== "%";
  const bases: ShareBase[] = ["row", ...(nested ? (["group"] as const) : []), ...(footer ? (["column", "overall"] as const) : [])];
  const [chosen, setChosen] = useState<ShareBase>("row");
  // Grupos abertos/fechados pelo usuário; sem escolha, abertos até COLLAPSE_AFTER linhas.
  const [toggled, setToggled] = useState<Record<string, boolean>>({});
  const isOpen = (g: Group) => toggled[g.head.key] ?? g.inner.length <= COLLAPSE_AFTER;
  const base: ShareBase = bases.includes(chosen) ? chosen : "row";
  const from = data.total_rows ? data.offset + 1 : 0;
  const to = Math.min(data.offset + data.limit, data.total_rows);
  const arrow = order === "desc" ? " ↓" : " ↑";

  // A linha selecionada (ex.: território clicado no mapa) fica à vista: se estiver
  // fora do quadro da tabela, a tabela rola por dentro até ela (a página não se move).
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = wrap.current;
    if (!box || !selected) return;
    const row = Array.from(box.querySelectorAll<HTMLTableRowElement>("tbody tr")).find(
      (tr) => tr.dataset.key === selected,
    );
    if (!row) return;
    const header = box.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    const b = box.getBoundingClientRect();
    const r = row.getBoundingClientRect();
    if (r.top >= b.top + header && r.bottom <= b.top + box.clientHeight) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    // Destino absoluto (e não um deslocamento): chamadas repetidas no meio da animação
    // continuam chegando ao mesmo lugar, com a linha centralizada abaixo do cabeçalho.
    const top = box.scrollTop + (r.top - b.top) - header - (box.clientHeight - header - r.height) / 2;
    box.scrollTo?.({ top: Math.max(0, top), behavior: reduce ? "auto" : "smooth" });
  }, [selected, data]);

  const valueWithShare = (row: Row, c: Column) => {
    const cell = row.cells[c.key];
    const denominator = shares ? shareBase(base, c, row, footer, totalKey) : null;
    const share = denominator && cell?.value != null ? (cell.value / denominator) * 100 : null;
    return (
      <>
        <span className="cell-value">{formatValue(cell?.value, cell?.status ?? "absent")}</span>
        {share !== null ? <span className="share"> ({formatShare(share)})</span> : null}
      </>
    );
  };

  // Célula de um grupo: o valor do grupo e, embaixo, as categorias detalhadas dentro dele.
  const groupCell = (row: Row, g: Group) => (
    <td key={g.head.key}>
      {g.inner.length && isOpen(g) ? (
        <div className="cell-group">
          <div className="cell-line cell-head">{valueWithShare(row, g.head)}</div>
          {g.inner.map((c) => (
            <div key={c.key} className="cell-line" style={{ paddingLeft: `${Math.max(0, c.depth - g.head.depth - 1) * 12}px` }}>
              <span className="cell-label">{innerLabel(g.head, c)}</span>
              <span>{valueWithShare(row, c)}</span>
            </div>
          ))}
        </div>
      ) : (
        valueWithShare(row, g.head)
      )}
    </td>
  );

  // "(%)" na unidade das colunas que mostram %: na linha e no grupo, todas menos o Total.
  const unitLine = (c: Column) =>
    shares && (base === "column" || base === "overall" || c.key !== totalKey) ? `${unit} (%)` : unit;

  return (
    <div className="table-box">
      {shares ? (
        <div className="share-base">
          {bases.length > 1 ? (
            <label>
              {t("shareOf")}
              <select value={base} onChange={(e) => setChosen(e.target.value as ShareBase)}>
                {bases.map((b) => (
                  <option key={b} value={b}>
                    {b === "column" && footer ? t("share.column", { name: footer.name }) : t(`share.${b}`)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <details className="method">
            <summary>{t("shareHow")}</summary>
            <p className="caption">
              {t(`shareNote.${base}`)} {t("shareNoteAll")}
            </p>
          </details>
        </div>
      ) : null}
      <div className="table-wrap" ref={wrap}>
        <table className={`data-table${nested ? " is-matrix" : ""}`}>
          <thead>
            <tr>
              <th scope="col">
                <button type="button" onClick={() => onSort("name")} aria-label={t("sortByName")}>
                  {t("territory")}
                  {sort === "name" ? arrow : ""}
                </button>
              </th>
              {groups.map((g, i) => (
                <th scope="col" key={g.head.key}>
                  {i === 0 ? (
                    <button type="button" onClick={() => onSort("value")} aria-label={t("sortByValue")}>
                      {g.head.label}
                      {sort === "value" ? arrow : ""}
                    </button>
                  ) : (
                    g.head.label
                  )}
                  <span className="th-unit">{unitLine(g.head)}</span>
                  {g.inner.length ? (
                    <button
                      type="button"
                      className="th-toggle"
                      aria-expanded={isOpen(g)}
                      onClick={() => setToggled((cur) => ({ ...cur, [g.head.key]: !isOpen(g) }))}
                    >
                      {isOpen(g) ? t("collapse") : t("expand", { count: g.inner.length })}
                    </button>
                  ) : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr
                key={r.geography_key}
                data-key={r.geography_key}
                aria-selected={selected === r.geography_key}
                onClick={() => onSelect(r.geography_key)}
              >
                <th scope="row" style={{ textAlign: "left", fontWeight: 400 }}>
                  {r.name}
                  {r.uf_abbreviation && !r.name.endsWith(r.uf_abbreviation) ? (
                    <span className="muted"> ({r.uf_abbreviation})</span>
                  ) : null}
                </th>
                {groups.map((g) => groupCell(r, g))}
              </tr>
            ))}
          </tbody>
          {footer ? (
            <tfoot>
              <tr>
                <th scope="row">{t("footer", { name: footer.name })}</th>
                {groups.map((g) => groupCell(footer, g))}
              </tr>
            </tfoot>
          ) : null}
        </table>
      </div>
      <div className="pager">
        <span>{t("page", { from, to, total: data.total_rows })}</span>
        <button type="button" disabled={data.offset === 0} onClick={() => onPage(Math.max(0, data.offset - data.limit))}>
          {t("previous")}
        </button>
        <button type="button" disabled={to >= data.total_rows} onClick={() => onPage(data.offset + data.limit)}>
          {t("next")}
        </button>
      </div>
    </div>
  );
}
