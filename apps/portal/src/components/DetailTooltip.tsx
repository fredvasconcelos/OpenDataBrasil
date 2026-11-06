"use client";

import { useTranslations } from "next-intl";

import { flattenDetail } from "@/lib/detail";
import { formatShare, formatValue, unitSuffix } from "@/lib/format";
import type { Detail } from "@/lib/types";

interface Props {
  name: string;
  detail: Detail | null;
  loading: boolean;
  x: number;
  y: number;
}

// Tooltip do mapa: só o território sob o ponteiro, com os sub-KPIs das dimensões
// marcadas (cor ou raça > sexo), cada percentual sobre o nó de cima.
export function DetailTooltip({ name, detail, loading, x, y }: Props) {
  const t = useTranslations("dashboard");
  const rows = detail ? flattenDetail(detail.root) : [];
  const left = typeof window !== "undefined" && x > window.innerWidth - 380 ? x - 370 : x + 16;
  return (
    <div className="tooltip" role="tooltip" style={{ left, top: y + 12 }}>
      <h3>
        {name}
        {detail ? <span className="muted small"> · {detail.period}</span> : null}
      </h3>
      {loading && !detail ? <p className="muted small">{t("loading")}</p> : null}
      {detail ? (
        <table>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} style={r.depth === 0 ? { fontWeight: 600 } : undefined}>
                <td style={{ paddingLeft: r.depth * 12 }}>{r.label}</td>
                <td className="num">{formatValue(r.value, r.status)}</td>
                <td className="share">{formatShare(r.share)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {detail ? (
        <p className="muted small" style={{ margin: "6px 0 0" }}>
          {unitSuffix(detail.unit)}
          {rows.some((r) => r.share !== null) ? ` · ${t("derivedNote")}` : ""}
        </p>
      ) : null}
    </div>
  );
}
