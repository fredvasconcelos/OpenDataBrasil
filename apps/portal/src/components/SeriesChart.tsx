"use client";

import { extent } from "d3-array";
import { scaleLinear, scalePoint } from "d3-scale";
import { area, line } from "d3-shape";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import {
  formatCompact,
  formatPeriod,
  formatValue,
  unitSuffix,
} from "@/lib/format";
import { CHART, SERIES } from "@/lib/theme";
import type { Series } from "@/lib/types";

const M = { top: 10, right: 16, bottom: 26, left: 60 };
const MAX_X_LABELS = 6;

type Point = { period: string; value: number | null; status?: string };
type Hover = { serie: number; period: string };

// Evolução temporal: uma linha por combinação de categorias, ausências interrompem a linha.
// Design System ODBr: paleta SERIES (10 cores, var(--odbr-series-N)) no lugar de
// schemeTableau10; série principal 2,5 px com área suave; demais 1,5 px; pontos com
// miolo na cor da superfície; no máximo 6 rótulos no eixo X. Desenhado no tamanho
// real do contêiner (o texto não encolhe com o cartão).
// Tooltip: passar o ponteiro (ou o foco do teclado) sobre um ponto mostra o período e o
// valor, com uma guia vertical e o ponto destacado. Sem <title> do SVG (o balão nativo
// é lento e destoa do Design System, mesma decisão do mapa).
export function SeriesChart({ data }: { data: Series }) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLDivElement>(null);
  const [{ W, H }, setSize] = useState({ W: 560, H: 220 });
  const [hover, setHover] = useState<Hover | null>(null);
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
  const periods = [
    ...new Set(data.series.flatMap((s) => s.points.map((p) => p.period))),
  ].sort();
  const values = data.series
    .flatMap((s) => s.points.map((p) => p.value))
    .filter((v): v is number => v !== null);
  const [lo, hi] = extent(values);
  const x = scalePoint<string>()
    .domain(periods)
    .range([M.left, W - M.right])
    .padding(0.4);
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
  const last = periods.length - 1;
  // Rótulos a cada `step` períodos e sempre o último; o vizinho próximo demais do
  // último é omitido para não sobrepor.
  const showLabel = (i: number) =>
    i === last || (i % step === 0 && last - i >= step);
  const color = (i: number) => SERIES[i % SERIES.length] as string;
  const unit = unitSuffix(data.unit);
  const tip = (() => {
    if (!hover) return null;
    const serie = data.series[hover.serie];
    const point = serie?.points.find((p) => p.period === hover.period);
    if (!serie || !point || point.value === null) return null;
    const px = x(point.period) ?? 0;
    // Perto das bordas o balão abre para dentro do gráfico.
    const side = px > W * 0.7 ? "end" : px < W * 0.3 ? "start" : "middle";
    return { serie, point, x: px, y: y(point.value), side, index: hover.serie };
  })();

  return (
    <figure className="series-figure">
      <div ref={box} className="series-plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          role="img"
          aria-label={`${t("seriesTitle")}: ${data.geography.name}`}
        >
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
              <text
                key={p}
                x={x(p)}
                y={H - 8}
                // O último rótulo alinha pela direita para não ser cortado na borda.
                textAnchor={
                  i === periods.length - 1 && periods.length > 1
                    ? "end"
                    : "middle"
                }
                fontSize="12"
                fontWeight="700"
                style={{ fill: CHART.label }}
              >
                {formatPeriod(p)}
              </text>
            ) : null,
          )}
          {data.series[0] ? (
            <path
              d={fill(data.series[0].points) ?? ""}
              style={{
                fill: color(0),
                fillOpacity: "var(--odbr-chart-area-opacity)",
              }}
            />
          ) : null}
          {tip ? (
            <line
              x1={tip.x}
              x2={tip.x}
              y1={M.top}
              y2={H - M.bottom}
              strokeDasharray="3 3"
              style={{ stroke: CHART.axis, pointerEvents: "none" }}
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
                .map((p) => {
                  const active =
                    hover?.serie === i && hover.period === p.period;
                  return (
                    <circle
                      key={p.period}
                      cx={x(p.period)}
                      cy={y(p.value ?? 0)}
                      r={(i === 0 ? 3.5 : 2.5) + (active ? 2 : 0)}
                      style={{
                        fill: active ? color(i) : CHART.surface,
                        stroke: color(i),
                        strokeWidth: 2,
                        pointerEvents: "none",
                      }}
                    />
                  );
                })}
              {s.points
                .filter((p) => p.value !== null)
                .map((p) => (
                  <circle
                    key={`hit-${p.period}`}
                    data-testid="series-point"
                    className="series-hit"
                    cx={x(p.period)}
                    cy={y(p.value ?? 0)}
                    r={10}
                    tabIndex={i === 0 ? 0 : -1}
                    onPointerEnter={() =>
                      setHover({ serie: i, period: p.period })
                    }
                    onPointerLeave={() => setHover(null)}
                    onFocus={() => setHover({ serie: i, period: p.period })}
                    onBlur={() => setHover(null)}
                  />
                ))}
            </g>
          ))}
        </svg>
        {tip ? (
          <div
            className={`chart-tip chart-tip-${tip.side}`}
            role="status"
            style={{ left: tip.x, top: tip.y }}
          >
            <span className="chart-tip-period">
              {formatPeriod(tip.point.period)}
            </span>
            <span className="chart-tip-value">
              {formatValue(tip.point.value, tip.point.status)}
              {unit ? <small> {unit}</small> : null}
            </span>
            {data.series.length > 1 ? (
              <span className="chart-tip-label">
                <i
                  aria-hidden="true"
                  style={{ background: color(tip.index) }}
                />
                {tip.serie.label}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
      <figcaption className="small">
        <ul className="series-legend">
          {data.series.map((s, i) => (
            <li key={s.key}>
              <span
                aria-hidden="true"
                style={{
                  width: 16,
                  height: 3,
                  borderRadius: 2,
                  background: color(i),
                }}
              />
              {s.label}
            </li>
          ))}
        </ul>
        {periods.length === 1 ? (
          <p className="muted">{t("singlePeriod")}</p>
        ) : null}
      </figcaption>
    </figure>
  );
}
