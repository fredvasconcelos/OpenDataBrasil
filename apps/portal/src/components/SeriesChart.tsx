"use client";

import { extent } from "d3-array";
import { scaleLinear, scalePoint } from "d3-scale";
import { area, line } from "d3-shape";
import { useTranslations } from "next-intl";
import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { formatCompact, formatValue, unitSuffix } from "@/lib/format";
import { formatPeriod, labelWidth, parsePeriods, timeTicks, typicalStep, type ParsedPeriod, type Tick } from "@/lib/period";
import { CHART, SERIES } from "@/lib/theme";
import type { Series } from "@/lib/types";

const M = { top: 12, right: 18, bottom: 28 };
const TIP_GAP = 12;
const TIP_PAD = 4;
const TIP_MAX_ROWS = 8;
const PAD_X = 12;

type Point = { period: string; value: number | null; status?: string };
type XY = { x: number; y: number };

// Evolução temporal (Design System ODBr, seção 9 · Séries).
// - Eixo X de TEMPO (lib/period): períodos ausentes deixam vão proporcional e são
//   ligados por traço pontilhado; rótulos em passos redondos que cabem na largura,
//   com o primeiro e o último período sempre visíveis e ancorados por dentro.
//   Códigos não reconhecidos → eixo ordinal com a mesma regra de rótulos.
// - Ausência de valor (sigilo, "…") interrompe a linha, sem pontilhado.
// - Tooltip HTML dentro de .series-plot: segue o período mais próximo do ponteiro,
//   abre à direita do ponto e vira para a esquerda/para baixo quando não cabe; nunca
//   sai do quadro (mede a própria caixa antes de pintar). Guia vertical tracejada.
// - Teclado: foco no gráfico, ← → percorrem os períodos, Home/End, Esc fecha.
// - Desenhado no tamanho real do contêiner (o texto não encolhe com o cartão).
export function SeriesChart({ data }: { data: Series }) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLDivElement>(null);
  const tip = useRef<HTMLDivElement>(null);
  const [{ W, H }, setSize] = useState({ W: 560, H: 260 });
  const [active, setActive] = useState<number | null>(null);
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

  const raws = [...new Set(data.series.flatMap((s) => s.points.map((p) => p.period)))];
  const parsed = parsePeriods(raws);
  const periods: string[] = parsed ? parsed.map((p) => p.raw) : [...raws].sort();
  const byRaw = new Map<string, ParsedPeriod>(parsed?.map((p) => [p.raw, p]) ?? []);
  const label = (raw: string) => {
    const p = byRaw.get(raw);
    return p ? formatPeriod(p) : raw;
  };

  const values = data.series.flatMap((s) => s.points.map((p) => p.value)).filter((v): v is number => v !== null);
  const [lo, hi] = extent(values);
  const y = scaleLinear()
    .domain([Math.min(0, lo ?? 0), hi ?? 1])
    .nice()
    .range([H - M.bottom, M.top]);
  const yTicks = y.ticks(5);
  // Margem esquerda pelo maior rótulo do eixo Y (milhões e decimais não cortam).
  const left = Math.max(40, ...yTicks.map((v) => labelWidth(formatCompact(v)) + 14));
  const x0 = left + PAD_X;
  const x1 = W - M.right - PAD_X;

  let xOf: (raw: string) => number;
  let tickX: (tk: Tick) => number;
  let ticks: Tick[];
  if (parsed && parsed.length) {
    const first = parsed[0] as ParsedPeriod;
    const last = parsed[parsed.length - 1] as ParsedPeriod;
    const xt = scaleLinear()
      .domain(first.t === last.t ? [first.t - 1, first.t + 1] : [first.t, last.t])
      .range([x0, x1]);
    xOf = (raw) => xt(byRaw.get(raw)?.t ?? first.t);
    // Ticks internos podem cair em períodos sem dado (ex.: 2010): posição pelo tempo.
    tickX = (tk) => xt(tk.t);
    ticks = timeTicks(parsed, x1 - x0, (v) => xt(v)).ticks;
    if (first.t === last.t) ticks = ticks.map((tk) => ({ ...tk, anchor: "middle" }));
  } else {
    const xp = scalePoint<string>().domain(periods).range([x0, x1]).padding(periods.length === 1 ? 0.5 : 0);
    xOf = (raw) => xp(raw) ?? x0;
    tickX = (tk) => xOf(tk.label);
    const widest = Math.max(...periods.map((p) => labelWidth(p)), 1);
    const room = Math.max(2, Math.floor((x1 - x0) / (widest + 16)));
    const step = Math.max(1, Math.ceil((periods.length - 1) / (room - 1)));
    const lastIndex = periods.length - 1;
    ticks = periods
      .map((p, i) => ({ p, i }))
      .filter(({ i }) => i === 0 || i === lastIndex || (i % step === 0 && lastIndex - i >= step / 2))
      .map(({ p, i }) => ({
        unit: i,
        t: i,
        label: p,
        anchor: periods.length === 1 ? "middle" : i === 0 ? "start" : i === lastIndex ? "end" : "middle",
      }));
  }

  // Vãos: períodos não publicados entre dois pontos válidos → pontilhado.
  const step = parsed ? typicalStep(parsed) : 1;
  const isGap = (a: string, b: string) => {
    const pa = byRaw.get(a);
    const pb = byRaw.get(b);
    return !!pa && !!pb && pb.unit - pa.unit > step * 1.5;
  };
  const sorted = (pts: readonly Point[]) => [...pts].sort((a, b) => periods.indexOf(a.period) - periods.indexOf(b.period));
  const runs = (pts: readonly Point[]) => {
    const solid: Point[][] = [];
    const dashed: [Point, Point][] = [];
    let run: Point[] = [];
    let prev: Point | null = null;
    for (const p of sorted(pts)) {
      if (p.value === null) {
        if (run.length) solid.push(run);
        run = [];
        prev = null;
        continue;
      }
      if (prev && isGap(prev.period, p.period)) {
        dashed.push([prev, p]);
        if (run.length) solid.push(run);
        run = [];
      }
      run.push(p);
      prev = p;
    }
    if (run.length) solid.push(run);
    return { solid, dashed };
  };

  // A área só se interrompe em ausência de valor; atravessa os vãos (sob o pontilhado).
  const areaRuns = (pts: readonly Point[]) => {
    const out: Point[][] = [];
    let run: Point[] = [];
    for (const p of sorted(pts)) {
      if (p.value === null) {
        if (run.length) out.push(run);
        run = [];
      } else run.push(p);
    }
    if (run.length) out.push(run);
    return out;
  };
  const draw = line<Point>()
    .x((p) => xOf(p.period))
    .y((p) => y(p.value ?? 0));
  const base = y(Math.max(0, y.domain()[0] ?? 0));
  const fill = area<Point>()
    .x((p) => xOf(p.period))
    .y0(base)
    .y1((p) => y(p.value ?? 0));
  const color = (i: number) => SERIES[i % SERIES.length] as string;
  const hasGaps = data.series.some((s) => runs(s.points).dashed.length > 0);

  // Hover: período mais próximo do ponteiro (no eixo de tempo, não no índice).
  const xs = periods.map((p) => xOf(p));
  const nearest = (px: number) => {
    let best = 0;
    for (let i = 1; i < xs.length; i++) if (Math.abs((xs[i] as number) - px) < Math.abs((xs[best] as number) - px)) best = i;
    return best;
  };
  const onMove = (e: PointerEvent<SVGRectElement>) => {
    const rect = e.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (!rect || !periods.length) return;
    setActive(nearest(e.clientX - rect.left));
  };
  const onKey = (e: KeyboardEvent<SVGSVGElement>) => {
    if (!periods.length) return;
    const lastIndex = periods.length - 1;
    const cur = active ?? lastIndex;
    const next =
      e.key === "ArrowLeft" ? Math.max(0, cur - 1)
      : e.key === "ArrowRight" ? Math.min(lastIndex, cur + 1)
      : e.key === "Home" ? 0
      : e.key === "End" ? lastIndex
      : null;
    if (e.key === "Escape") setActive(null);
    if (next === null) return;
    e.preventDefault();
    setActive(next);
  };

  const period = active === null ? null : (periods[active] ?? null);
  const rows =
    period === null
      ? []
      : data.series.map((s, i) => {
          const p = s.points.find((pt) => pt.period === period);
          return { key: s.key, label: s.label, color: color(i), value: p?.value ?? null, status: p?.status ?? "absent" };
        });
  const anchor: XY | null =
    period === null
      ? null
      : {
          x: xOf(period),
          y: Math.min(...rows.filter((r) => r.value !== null).map((r) => y(r.value as number)), H - M.bottom),
        };

  // Posiciona o tooltip depois de medir: direita do ponto → esquerda; acima → abaixo;
  // sempre dentro do quadro (TIP_PAD).
  useLayoutEffect(() => {
    const el = tip.current;
    if (!el || !anchor) return;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    let lx = anchor.x + TIP_GAP;
    if (lx + w > W - TIP_PAD) lx = anchor.x - TIP_GAP - w;
    lx = Math.max(TIP_PAD, Math.min(lx, W - w - TIP_PAD));
    let ty = anchor.y - h - TIP_GAP;
    if (ty < TIP_PAD) ty = anchor.y + TIP_GAP;
    ty = Math.max(TIP_PAD, Math.min(ty, H - h - TIP_PAD));
    el.style.left = `${lx}px`;
    el.style.top = `${ty}px`;
    el.style.visibility = "visible";
  });

  const unit = unitSuffix(data.unit);
  const shown = rows.slice(0, TIP_MAX_ROWS);
  const hidden = rows.length - shown.length;
  const summary = period === null ? "" : `${label(period)}: ${rows.map((r) => `${r.label} ${formatValue(r.value, r.status)}`).join("; ")}`;

  return (
    <figure className="series-figure">
      <div ref={box} className="series-plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          role="img"
          aria-label={`${t("seriesTitle")}: ${data.geography.name}. ${t("seriesKeys")}`}
          tabIndex={0}
          onKeyDown={onKey}
          onBlur={() => setActive(null)}
        >
          {yTicks.map((tick) => (
            <g key={tick}>
              <line x1={left} x2={W - M.right} y1={y(tick)} y2={y(tick)} style={{ stroke: tick === 0 ? CHART.axis : CHART.grid }} />
              <text
                x={left - 8}
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
          {ticks.map((tk) => {
            const tx = tickX(tk);
            return (
              <g key={`${tk.unit}-${tk.label}`} className="series-tick">
                <line x1={tx} x2={tx} y1={H - M.bottom} y2={H - M.bottom + 4} style={{ stroke: CHART.axis }} />
                <text x={tx} y={H - 8} textAnchor={tk.anchor} fontSize="12" fontWeight="700" style={{ fill: CHART.label }}>
                  {tk.label}
                </text>
              </g>
            );
          })}
          {data.series[0]
            ? areaRuns(data.series[0].points).map((run) => (
                <path
                  key={`area-${run[0]?.period}`}
                  d={fill(run) ?? ""}
                  style={{ fill: color(0), fillOpacity: "var(--odbr-chart-area-opacity)" }}
                />
              ))
            : null}
          {period !== null && anchor ? (
            <line
              className="series-guide"
              x1={anchor.x}
              x2={anchor.x}
              y1={M.top}
              y2={H - M.bottom}
              style={{ stroke: CHART.axis }}
              strokeDasharray="3 3"
            />
          ) : null}
          {data.series.map((s, i) => {
            const { solid, dashed } = runs(s.points);
            const width = i === 0 ? 2.5 : 1.5;
            return (
              <g key={s.key}>
                {dashed.map(([a, b]) => (
                  <line
                    key={`gap-${a.period}`}
                    className="series-gap"
                    x1={xOf(a.period)}
                    y1={y(a.value ?? 0)}
                    x2={xOf(b.period)}
                    y2={y(b.value ?? 0)}
                    strokeDasharray="2 4"
                    strokeLinecap="round"
                    style={{ stroke: color(i), strokeWidth: width, strokeOpacity: 0.7 }}
                  />
                ))}
                {solid.map((run) => (
                  <path
                    key={`line-${run[0]?.period}`}
                    d={draw(run) ?? ""}
                    fill="none"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    style={{ stroke: color(i), strokeWidth: width }}
                  />
                ))}
                {s.points
                  .filter((p) => p.value !== null)
                  .map((p) => {
                    const on = p.period === period;
                    return (
                      <circle
                        key={p.period}
                        cx={xOf(p.period)}
                        cy={y(p.value ?? 0)}
                        r={(i === 0 ? 3.5 : 2.5) + (on ? 1.5 : 0)}
                        style={{ fill: on ? color(i) : CHART.surface, stroke: color(i), strokeWidth: 2 }}
                      />
                    );
                  })}
              </g>
            );
          })}
          <rect
            className="series-hit"
            x={left}
            y={M.top}
            width={Math.max(0, W - M.right - left)}
            height={Math.max(0, H - M.bottom - M.top)}
            fill="transparent"
            onPointerMove={onMove}
            onPointerDown={onMove}
            onPointerLeave={() => setActive(null)}
          />
        </svg>
        {period !== null ? (
          <div ref={tip} className="series-tip" role="tooltip" style={{ visibility: "hidden" }}>
            <div className="series-tip-head">{label(period)}</div>
            <ul>
              {shown.map((r) => (
                <li key={r.key}>
                  <span className="series-tip-dot" style={{ background: r.color }} aria-hidden="true" />
                  {data.series.length > 1 ? <span className="series-tip-label">{r.label}</span> : null}
                  <span className="series-tip-value">{formatValue(r.value, r.status)}</span>
                </li>
              ))}
            </ul>
            {hidden > 0 ? <div className="series-tip-more">{t("seriesMore", { count: hidden })}</div> : null}
            <div className="series-tip-unit">{unit}</div>
          </div>
        ) : null}
        <span className="sr-only" aria-live="polite">
          {summary}
        </span>
      </div>
      <figcaption className="small">
        <ul className="series-legend">
          {data.series.map((s, i) => (
            <li key={s.key}>
              <span aria-hidden="true" style={{ width: 16, height: 3, borderRadius: 2, background: color(i) }} />
              {s.label}
            </li>
          ))}
          {hasGaps ? (
            <li className="series-legend-gap">
              <svg width="16" height="4" aria-hidden="true">
                <line x1="1" y1="2" x2="15" y2="2" strokeDasharray="2 4" strokeLinecap="round" style={{ stroke: CHART.label, strokeWidth: 2 }} />
              </svg>
              {t("gapNote")}
            </li>
          ) : null}
        </ul>
        {periods.length === 1 ? <p className="muted">{t("singlePeriod")}</p> : null}
      </figcaption>
    </figure>
  );
}

