"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { formatCount, type DatasetItem, type DatasetSort } from "@/lib/metrics";

interface Props {
  items: readonly DatasetItem[];
  sort: DatasetSort;
  onSort: (sort: DatasetSort) => void;
  /** Período por extenso, junto dos números. */
  period: string;
}

// Conjuntos de dados mais acessados (DS 2.12). A unidade é o indicador (ADR-0027, item 7),
// que é o que o visitante abre e exporta; o link leva ao Painel. A ordem (visualizações ou
// downloads) vem da API. No celular, a tabela vira lista (CSS).
export function TopDatasets({ items, sort, onSort, period }: Props) {
  const t = useTranslations("metrics.datasets");
  return (
    <section className="card metrics-block" aria-labelledby="metricas-conjuntos">
      <div className="metrics-block-head">
        <h2 id="metricas-conjuntos">{t("title")}</h2>
        <div className="segmented" role="group" aria-label={t("sort")}>
          <button type="button" aria-pressed={sort === "views"} onClick={() => onSort("views")}>
            {t("byViews")}
          </button>
          <button type="button" aria-pressed={sort === "downloads"} onClick={() => onSort("downloads")}>
            {t("byDownloads")}
          </button>
        </div>
      </div>
      <p className="muted metrics-period-line">{period}</p>
      {items.length ? (
        <table className="data-table top-datasets">
          <thead>
            <tr>
              <th scope="col">{t("rank")}</th>
              <th scope="col">{t("name")}</th>
              <th scope="col">{t("theme")}</th>
              <th scope="col" className="num" aria-sort={sort === "views" ? "descending" : undefined}>
                {t("views")}
              </th>
              <th scope="col" className="num" aria-sort={sort === "downloads" ? "descending" : undefined}>
                {t("downloads")}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((d, i) => (
              <tr key={d.kpi_id}>
                <td data-label={t("rank")}>{i + 1}</td>
                <th scope="row" data-label={t("name")}>
                  <Link href={`/dashboard?kpi=${encodeURIComponent(d.kpi_id)}`}>{d.title}</Link>
                </th>
                <td data-label={t("theme")}>{d.theme}</td>
                <td className="num" data-label={t("views")}>
                  {formatCount(d.views)}
                </td>
                <td className="num" data-label={t("downloads")}>
                  {formatCount(d.downloads)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">{t("empty")}</p>
      )}
    </section>
  );
}
