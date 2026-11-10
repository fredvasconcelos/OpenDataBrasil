"use client";

import { extent } from "d3-array";
import { scaleLinear, scalePoint } from "d3-scale";
import { area, line } from "d3-shape";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { formatCompact, formatValue } from "@/lib/format";
import { CHART, SERIES } from "@/lib/theme";
import type { Series } from "@/lib/types";

const M = { top: 10, right: 16, bottom: 26, left: 60 };
const MAX_X_LABELS = 6;

type Point = { period: string; value: number | null };

// Evolução temporal: uma linha por combinação de categorias, ausências interrompem a linha.
// Design System ODBr: paleta SERIES (10 cores, var(--odbr-series-N)) no lugar de
// schemeTableau10; série principal 2,5 px com área suave; demais 1,5 px; pontos com
// miolo na cor da superfície; no máximo 6 rótulos no eixo X. Desenhado no tamanho
// real do contêiner (o texto não encolhe com o cartão).
export function SeriesChart({ data }: { data: Series }) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLDivElement>(null);
  const [{ W, H }, setSize] = useState({ W: 560, H: 220 });
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setSize({ W: width, H: height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const periods = [...new Set(data.series.flatMap((s) => s.points.map((p) => p.period)))].sort();
  const values = data.series.flatMap((s) => s.points.map((p) => p.value)).filter((v): v is number => v !== null);
  const [lo, hi] = extent(values);
  const x = scalePoint<string>().domain(periods).range([M.left, W - M.right]).padding(0.4);
  const y = scaleLinear()
    .domain([Math.min(0, lo ?? 0), hi ?? 1])
    .nice()
    .range([H - M.bottom, M.top]);
  const draw = line<Point>()
    .defined((p) => p.value !== null)
    .x((p) => x(p.period) ?? 0)
    .y((p) => y(p.value ?? 0));
  const fill = area<Point>()
    .defined((p) => p.value !== null)
    .x((p) => x(p.period) ?? 0)
    .y0(y(Math.max(0, y.domain()[0] ?? 0)))
    .y1((p) => y(p.value ?? 0));
  const step = Math.max(1, Math.ceil(periods.length / MAX_X_LABELS));
  const showLabel = (i: number) => i % step === 0 || i === periods.length - 1;
  const color = (i: number) => SERIES[i % SERIES.length] as string;

  return (
    <figure className="series-figure">
      <div ref={box} className="series-plot">
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={`${t("seriesTitle")}: ${data.geography.name}`}>
          {y.ticks(5).map((tick) => (
            <g key={tick}>
              <line
                x1={M.left}
                x2={W - M.right}
                y1={y(tick)}
                y2={y(tick)}
                style={{ stroke: tick === 0 ? CHART.axis : CHART.grid }}
              />
              <text
                x={M.left - 8}
                y={y(tick)}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize="12"
                fontWeight="700"
                style={{ fill: CHART.label }}
              >
                {formatCompact(tick)}
              </text>
            </g>
          ))}
          {periods.map((p, i) =>
            showLabel(i) ? (
              <text key={p} x={x(p)} y={H - 8} textAnchor="middle" fontSize="12" fontWeight="700" style={{ fill: CHART.label }}>
                {p}
              </text>
            ) : null,
          )}
          {data.series[0] ? (
            <path
              d={fill(data.series[0].points) ?? ""}
              style={{ fill: color(0), fillOpacity: "var(--odbr-chart-area-opacity)" }}
            />
          ) : null}
          {data.series.map((s, i) => (
            <g key={s.key}>
              <path
                d={draw(s.points) ?? ""}
                fill="none"
                strokeLinejoin="round"
                strokeLinecap="round"
                style={{ stroke: color(i), strokeWidth: i === 0 ? 2.5 : 1.5 }}
              />
              {s.points
                .filter((p) => p.value !== null)
                .map((p) => (
                  <circle
                    key={p.period}
                    cx={x(p.period)}
                    cy={y(p.value ?? 0)}
                    r={i === 0 ? 3.5 : 2.5}
                    style={{ fill: CHART.surface, stroke: color(i), strokeWidth: 2 }}
                  >
                    <title>{`${s.label} · ${p.period}: ${formatValue(p.value, p.status)}`}</title>
                  </circle>
                ))}
            </g>
          ))}
        </svg>
      </div>
      <figcaption className="small">
        <ul className="series-legend">
          {data.series.map((s, i) => (
            <li key={s.key}>
              <span aria-hidden="true" style={{ width: 16, height: 3, borderRadius: 2, background: color(i) }} />
              {s.label}
            </li>
          ))}
        </ul>
        {periods.length === 1 ? <p className="muted">{t("singlePeriod")}</p> : null}
      </figcaption>
    </figure>
  );
}
