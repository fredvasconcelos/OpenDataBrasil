"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { formatShare, formatValue, unitShort } from "@/lib/format";
import type { Table } from "@/lib/types";

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
  // Unidade no cabeçalho de cada coluna: "Total (%)", "Alimentação (R$)" (DS 2.3.6).
  const unit = unitShort(data.unit);
  const totalKey = data.columns[0]?.key;
  const t = useTranslations("table");
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

  return (
    <div className="table-box">
      <div className="table-wrap" ref={wrap}>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">
                <button type="button" onClick={() => onSort("name")} aria-label={t("sortByName")}>
                  {t("territory")}
                  {sort === "name" ? arrow : ""}
                </button>
              </th>
              {data.columns.map((c, i) => (
                <th scope="col" key={c.key} style={{ fontWeight: c.depth ? 400 : 600 }}>
                  {i === 0 ? (
                    <button type="button" onClick={() => onSort("value")} aria-label={t("sortByValue")}>
                      {c.label} ({unit})
                      {sort === "value" ? arrow : ""}
                    </button>
                  ) : (
                    `${c.label} (${unit})`
                  )}
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
                {data.columns.map((c) => {
                  const cell = r.cells[c.key];
                  const total = totalKey ? r.cells[totalKey]?.value : null;
                  // Aditivo: a categoria mostra também o % do Total do território.
                  const share =
                    additive && c.key !== totalKey && unit !== "%" && cell?.value != null && total
                      ? (cell.value / total) * 100
                      : null;
                  return (
                    <td key={c.key}>
                      {formatValue(cell?.value, cell?.status ?? "absent")}
                      {share !== null ? <span className="share"> ({formatShare(share)})</span> : null}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
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
