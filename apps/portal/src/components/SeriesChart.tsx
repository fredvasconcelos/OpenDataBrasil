"use client";

import { extent } from "d3-array";
import { scaleLinear, scalePoint } from "d3-scale";
import { schemeTableau10 } from "d3-scale-chromatic";
import { line } from "d3-shape";
import { useTranslations } from "next-intl";

import { formatCompact, formatValue } from "@/lib/format";
import type { Series } from "@/lib/types";

const W = 560;
const H = 260;
const M = { top: 12, right: 16, bottom: 28, left: 64 };

// Evolução temporal: uma linha por combinação de categorias, ausências interrompem a linha.
export function SeriesChart({ data }: { data: Series }) {
  const t = useTranslations("dashboard");
  const periods = [...new Set(data.series.flatMap((s) => s.points.map((p) => p.period)))].sort();
  const values = data.series.flatMap((s) => s.points.map((p) => p.value)).filter((v): v is number => v !== null);
  const [lo, hi] = extent(values);
  const x = scalePoint<string>().domain(periods).range([M.left, W - M.right]).padding(0.4);
  const y = scaleLinear()
    .domain([Math.min(0, lo ?? 0), hi ?? 1])
    .nice()
    .range([H - M.bottom, M.top]);
  const draw = line<{ period: string; value: number | null }>()
    .defined((p) => p.value !== null)
    .x((p) => x(p.period) ?? 0)
    .y((p) => y(p.value ?? 0));
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${t("seriesTitle")}: ${data.geography.name}`} width="100%">
        {y.ticks(5).map((tick) => (
          <g key={tick}>
            <line x1={M.left} x2={W - M.right} y1={y(tick)} y2={y(tick)} stroke="#eceff3" />
            <text x={M.left - 6} y={y(tick)} textAnchor="end" dominantBaseline="middle" fontSize="11" fill="#5b6475">
              {formatCompact(tick)}
            </text>
          </g>
        ))}
        {periods.map((p) => (
          <text key={p} x={x(p)} y={H - 8} textAnchor="middle" fontSize="11" fill="#5b6475">
            {p}
          </text>
        ))}
        {data.series.map((s, i) => {
          const color = schemeTableau10[i % 10] ?? "#333";
          return (
            <g key={s.key}>
              <path d={draw(s.points) ?? ""} fill="none" stroke={color} strokeWidth={i === 0 ? 2.5 : 1.5} />
              {s.points
                .filter((p) => p.value !== null)
                .map((p) => (
                  <circle key={p.period} cx={x(p.period)} cy={y(p.value ?? 0)} r={3} fill={color}>
                    <title>{`${s.label} · ${p.period}: ${formatValue(p.value, p.status)}`}</title>
                  </circle>
                ))}
            </g>
          );
        })}
      </svg>
      <figcaption className="small">
        <ul style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", listStyle: "none", padding: 0, margin: 0 }}>
          {data.series.map((s, i) => (
            <li key={s.key}>
              <span style={{ color: schemeTableau10[i % 10] }}>■</span> {s.label}
            </li>
          ))}
        </ul>
        {periods.length === 1 ? <p className="muted">{t("singlePeriod")}</p> : null}
      </figcaption>
    </figure>
  );
}
