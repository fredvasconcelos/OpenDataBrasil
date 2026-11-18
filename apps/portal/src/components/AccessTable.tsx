"use client";

import { useTranslations } from "next-intl";

import { useValueLabels } from "@/components/useValueLabels";
import { formatPct, viewsText, type GeoItem } from "@/lib/metrics";

interface Props {
  items: readonly GeoItem[];
  /** Nome do nível ("País", "Grande Região", "Estado"). */
  levelLabel: string;
  selected: string | null;
  onSelect: (key: string) => void;
}

// O mapa como tabela (DS 2.12): os mesmos valores do mapa, na mesma ordem do ranking.
// Substitui o DataTable (que saiu no DS 2.9) como alternativa acessível ao mapa.
export function AccessTable({ items, levelLabel, selected, onSelect }: Props) {
  const t = useTranslations("metrics.table");
  const labels = useValueLabels();
  const rows = [...items].sort((a, b) => (b.views ?? 0) - (a.views ?? 0) || a.name.localeCompare(b.name, "pt-BR"));
  return (
    <table className="data-table access-table">
      <caption>{t("caption", { level: levelLabel.toLowerCase() })}</caption>
      <thead>
        <tr>
          <th scope="col">{t("place")}</th>
          <th scope="col" className="num">
            {t("views")}
          </th>
          <th scope="col" className="num">
            {t("share")}
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((item) => (
          <tr key={item.geography_key} className={item.geography_key === selected ? "is-active" : undefined}>
            <th scope="row">
              <button type="button" className="link-btn" onClick={() => onSelect(item.geography_key)}>
                {item.name}
              </button>
            </th>
            <td className="num">{viewsText(item, labels)}</td>
            <td className="num">{item.status === "ok" && item.share_pct !== null ? formatPct(item.share_pct) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
