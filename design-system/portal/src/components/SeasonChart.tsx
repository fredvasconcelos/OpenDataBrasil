"use client";

import { scaleBand, scaleLinear } from "d3-scale";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { formatCompact, formatValue, unitSuffix } from "@/lib/format";
import { CHART, SERIES } from "@/lib/theme";
import type { Series } from "@/lib/types";

// "Isolar período" (DS 2.3.14): a parte do ano (mês, trimestre ou semestre) isolada dos
// anos. Cada barra é o acumulado de todos os anos publicados nessa parte (fluxos) ou a
// média deles (índices, taxas, médias), para ver a sazonalidade: os meses com mais
// feminicídios, por exemplo.

const M = { top: 12, right: 12, bottom: 28 };
const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** Parte do ano de um código de período da Gold: "2025M08" → "M08"; "2025T3" → "T3". */
export function partOf(period: string): string | null {
  const m = /^\d{4}([MTS]\d{1,2})$/.exec(period);
  return m ? (m[1] as string) : null;
}

export function partLabel(part: string): string {
  if (part.startsWith("M")) return MONTHS[Number(part.slice(1)) - 1] ?? part;
  return part;
}

export interface SeasonBar {
  part: string;
  values: (number | null)[]; // uma por série
  years: number[]; // anos com valor, por série
}

/** Acumula (soma) ou tira a média, por parte do ano, de cada série. */
export function seasonBars(data: Series, rule: string | null | undefined): { bars: SeasonBar[]; labels: string[] } {
  // Com detalhe, o Total sai (como no gráfico de evolução): só as séries mais detalhadas.
  const deepest = Math.max(0, ...data.series.map((s) => s.depth ?? 0));
  const shown = deepest > 0 ? data.series.filter((s) => (s.depth ?? 0) === deepest) : data.series;
  const parts = [...new Set(shown.flatMap((s) => s.points.map((p) => partOf(p.period)).filter((x): x is string => !!x)))].sort();
  const mean = rule && rule !== "sum";
  const bars = parts.map((part) => {
    const per = shown.map((s) => {
      const vals = s.points.filter((p) => partOf(p.period) === part && p.value !== null).map((p) => p.value as number);
      if (!vals.length) return { v: null, n: 0 };
      const sum = vals.reduce((a, b) => a + b, 0);
      return { v: mean ? sum / vals.length : sum, n: vals.length };
    });
    return { part, values: per.map((x) => x.v), years: per.map((x) => x.n) };
  });
  return { bars, labels: shown.map((s) => s.label) };
}

export function SeasonChart({ data, rule }: { data: Series; rule?: string | null }) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLDivElement>(null);
  const [{ W, H }, setSize] = useState({ W: 560, H: 260 });
  const [active, setActive] = useState<number | null>(null);
  useEffect(() => {
    const el = box.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      setSize({ W: Math.max(280, entry.contentRect.width), H: Math.max(200, entry.contentRect.height) });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { bars, labels } = seasonBars(data, rule);
  const all = bars.flatMap((b) => b.values).filter((v): v is number => v !== null);
  const y = scaleLinear().domain([0, Math.max(...all, 1)]).nice().range([H - M.bottom, M.top]);
  const left = 48;
  const x = scaleBand<string>().domain(bars.map((b) => b.part)).range([left, W - M.right]).padding(0.2);
  const inner = scaleBand<number>()
    .domain(labels.map((_, i) => i))
    .range([0, x.bandwidth()])
    .padding(0.08);
  const color = (i: number) => SERIES[i % SERIES.length] as string;
  const years = Math.max(0, ...bars.flatMap((b) => b.years));
  const how = rule && rule !== "sum" ? t("isolateMean", { years }) : t("isolateSum", { years });
  const current = active === null ? null : bars[active];

  return (
    <figure className="series-figure season-figure">
      <div ref={box} className="series-plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          role="img"
          aria-label={`${t("isolate")}: ${how}`}
          onPointerLeave={() => setActive(null)}
        >
          {y.ticks(4).map((tick) => (
            <g key={tick}>
              <line x1={left} x2={W - M.right} y1={y(tick)} y2={y(tick)} style={{ stroke: tick === 0 ? CHART.axis : CHART.grid }} />
              <text x={left - 6} y={y(tick)} dy="0.32em" textAnchor="end" fontSize="12" fontWeight="700" style={{ fill: CHART.label }}>
                {formatCompact(tick)}
              </text>
            </g>
          ))}
          {bars.map((b, i) => (
            <g key={b.part} onPointerEnter={() => setActive(i)} onPointerDown={() => setActive(i)}>
              <rect x={x(b.part)} y={M.top} width={x.bandwidth()} height={H - M.bottom - M.top} fill="transparent" />
              {b.values.map((v, j) =>
                v === null ? null : (
                  <rect
                    key={j}
                    className="season-bar"
                    x={(x(b.part) ?? 0) + (inner(j) ?? 0)}
                    y={y(v)}
                    width={inner.bandwidth()}
                    height={Math.max(0, y(0) - y(v))}
                    rx={2}
                    style={{ fill: color(j), opacity: active === null || active === i ? 1 : 0.45 }}
                  />
                ),
              )}
              <text x={(x(b.part) ?? 0) + x.bandwidth() / 2} y={H - 8} textAnchor="middle" fontSize="12" fontWeight="700" style={{ fill: CHART.label }}>
                {partLabel(b.part)}
              </text>
            </g>
          ))}
        </svg>
        {current ? (
          <div className="series-tip" role="tooltip" style={{ left: Math.min((x(current.part) ?? 0) + x.bandwidth() + 8, W - 200), top: 8, visibility: "visible" }}>
            <div className="series-tip-head">{partLabel(current.part)}</div>
            <ul>
              {current.values.map((v, j) => (
                <li key={labels[j]}>
                  <span className="series-tip-dot" style={{ background: color(j) }} aria-hidden="true" />
                  {labels.length > 1 ? <span className="series-tip-label">{labels[j]}</span> : null}
                  <span className="series-tip-value">{formatValue(v, v === null ? "absent" : "valid")}</span>
                </li>
              ))}
            </ul>
            <div className="series-tip-unit">{unitSuffix(data.unit)}</div>
          </div>
        ) : null}
      </div>
      <figcaption className="small">
        {labels.length > 1 ? (
          <ul className="series-legend">
            {labels.map((l, j) => (
              <li key={l}>
                <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 2, background: color(j) }} />
                {l}
              </li>
            ))}
          </ul>
        ) : null}
        <p className="muted">{how}</p>
      </figcaption>
    </figure>
  );
}
