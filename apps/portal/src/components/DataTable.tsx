"use client";

import { useTranslations } from "next-intl";

import { formatValue } from "@/lib/format";
import type { Table } from "@/lib/types";

interface Props {
  data: Table;
  selected: string | null;
  sort: "value" | "name";
  order: "asc" | "desc";
  onSort: (sort: "value" | "name") => void;
  onPage: (offset: number) => void;
  onSelect: (key: string) => void;
}

export function DataTable({ data, selected, sort, order, onSort, onPage, onSelect }: Props) {
  const t = useTranslations("table");
  const from = data.total_rows ? data.offset + 1 : 0;
  const to = Math.min(data.offset + data.limit, data.total_rows);
  const arrow = order === "desc" ? " ↓" : " ↑";
  return (
    <div className="table-box">
      <div className="table-wrap">
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
                      {c.label}
                      {sort === "value" ? arrow : ""}
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr
                key={r.geography_key}
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
                  return <td key={c.key}>{formatValue(cell?.value, cell?.status ?? "absent")}</td>;
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
