"use client";

import { geoMercator, geoPath } from "d3-geo";
import { select } from "d3-selection";
import "d3-transition";
import { zoom, zoomIdentity, zoomTransform, type D3ZoomEvent, type ZoomBehavior, type ZoomTransform } from "d3-zoom";
import { useTranslations } from "next-intl";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type ReactNode } from "react";

import { formatCompact, formatValue } from "@/lib/format";
import { rewindForD3 } from "@/lib/geo";
import { quantileScale } from "@/lib/scale";
import { CHART } from "@/lib/theme";
import type { GeoCollection, GeoFeature, MapValue } from "@/lib/types";
import { fitView, MAX_SCALE, zoomDecision } from "@/lib/zoom";

/** Pedido de enquadramento: território (ou null = Brasil inteiro); `n` muda a cada pedido. */
export interface FitRequest {
  key: string | null;
  n: number;
}

interface Props {
  /** Territórios coloridos: o nível exibido, dentro do recorte quando houver. */
  collection: GeoCollection;
  /** Nível do recorte no país inteiro (desenhado em cinza fora do recorte); null sem recorte. */
  context: GeoCollection | null;
  values: MapValue[];
  selected: string | null;
  /** Recorte atual (contornado por cima de tudo). */
  focus: string | null;
  /** Há recorte ou nível acima para onde voltar ao afastar. */
  canUp: boolean;
  /** Dados do próximo nível ainda carregando. */
  loading?: boolean;
  fitRequest?: FitRequest | null;
  onHover: (key: string | null, name: string, event: { clientX: number; clientY: number }) => void;
  onSelect: (key: string) => void;
  /** Abrir o recorte no território; devolve se houve aprofundamento. */
  onDrill: (key: string, source: "click" | "gesture") => boolean;
  /** Voltar ao recorte (ou nível) de cima. */
  onUp: () => void;
  /** Voltar ao Brasil inteiro no primeiro nível. */
  onReset: () => void;
  label: string;
  /** Sobreposições do painel (ex.: trilha do recorte). */
  children?: ReactNode;
}

const STEP = 1.6;
const DURATION = 550;
// Acima disso o contorno fica mais fino (municípios: 5.570 polígonos).
const DENSE = 500;
const HATCH_ID = "odbr-hatch";

interface Shape {
  id: string;
  name: string;
  feature: GeoFeature;
  d: string;
}

// Mapa coroplético em SVG com ampliação seletiva (src/lib/zoom.ts).
// d3-geo calcula projeção e caminhos, d3-scale as cores e d3-zoom o zoom e o
// arraste; o React desenha. A transformação do zoom vai direto no <g>, sem novo
// render a cada quadro. Cores por var(--odbr-…) aplicadas em `style` (var() não
// funciona em atributos de apresentação do SVG); estados no globals.css.
export const MapView = forwardRef<SVGSVGElement | null, Props>(function MapView(
  {
    collection,
    context,
    values,
    selected,
    focus,
    canUp,
    loading = false,
    fitRequest = null,
    onHover,
    onSelect,
    onDrill,
    onUp,
    onReset,
    label,
    children,
  },
  ref,
) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLDivElement>(null);
  const svgEl = useRef<SVGSVGElement>(null);
  const layer = useRef<SVGGElement>(null);
  const behavior = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  // Tamanho provisório até o ResizeObserver medir o painel (measured).
  const [size, setSize] = useState({ width: 800, height: 480, measured: false });
  useImperativeHandle(ref, () => svgEl.current as SVGSVGElement, []);

  // Estado do gesto (fora do React): escala em que o recorte atual foi aberto,
  // escala no início do gesto, se a última transição veio dos botões +/− e o último
  // ponteiro. Transições (sem evento de origem) só contam como gesto quando vêm dos
  // botões; as de enquadramento só fixam a nova escala-base, mesmo se interrompidas.
  const gesture = useRef({ base: 1, start: 1, button: false, pointer: null as { x: number; y: number } | null });
  // Valores mais recentes para os ouvintes do d3, registrados uma vez só.
  const latest = useRef({ canUp, onDrill, onUp, onReset });
  useEffect(() => {
    latest.current = { canUp, onDrill, onUp, onReset };
  });

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setSize({ width, height, measured: true });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Território sob um ponto da tela (camada colorida ou de contexto).
  const keyAt = useCallback((x: number, y: number): string | null => {
    const hit = document.elementFromPoint(x, y)?.closest("path[data-key]");
    return hit?.getAttribute("data-key") ?? null;
  }, []);

  // Zoom e arraste. O duplo clique padrão do d3 dá lugar à abertura do recorte.
  useEffect(() => {
    const svg = svgEl.current;
    const g = layer.current;
    if (!svg || !g) return;
    const z = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, MAX_SCALE])
      .on("start", (e: D3ZoomEvent<SVGSVGElement, unknown>) => {
        gesture.current.start = e.transform.k;
      })
      .on("zoom", (e: D3ZoomEvent<SVGSVGElement, unknown>) => {
        g.setAttribute("transform", e.transform.toString());
      })
      .on("end", (e: D3ZoomEvent<SVGSVGElement, unknown>) => {
        const state = gesture.current;
        const k = e.transform.k;
        if (!e.sourceEvent) {
          if (!state.button) {
            state.base = k;
            return;
          }
          state.button = false;
        }
        // Clique ou arraste sem mudar a escala: nada a decidir.
        if (Math.abs(k - state.start) < 1e-6) return;
        const cur = latest.current;
        const decision = zoomDecision(k, state.base, cur.canUp);
        if (decision === "reset") {
          state.base = 1;
          cur.onReset();
        } else if (decision === "up") {
          state.base = k;
          cur.onUp();
        } else if (decision === "drill") {
          const source = e.sourceEvent as { clientX?: number; clientY?: number } | null;
          const r = svg.getBoundingClientRect();
          const x = source?.clientX ?? state.pointer?.x ?? r.left + r.width / 2;
          const y = source?.clientY ?? state.pointer?.y ?? r.top + r.height / 2;
          const key = keyAt(x, y) ?? keyAt(r.left + r.width / 2, r.top + r.height / 2);
          if (key && cur.onDrill(key, "gesture")) state.base = k;
        }
      });
    const sel = select(svg);
    sel.call(z).on("dblclick.zoom", null);
    behavior.current = z;
    return () => {
      sel.on(".zoom", null);
      behavior.current = null;
    };
  }, [keyAt]);

  useEffect(() => {
    behavior.current
      ?.extent([
        [0, 0],
        [size.width, size.height],
      ])
      .translateExtent([
        [0, 0],
        [size.width, size.height],
      ]);
  }, [size]);

  const animate = useCallback((to: ZoomTransform) => {
    const svg = svgEl.current;
    const z = behavior.current;
    if (!svg || !z) return;
    gesture.current.button = false;
    select(svg).transition().duration(DURATION).call(z.transform, to);
  }, []);

  // Botões + e −: zoom pelo centro, decidido como um gesto do usuário.
  const zoomBy = useCallback(
    (factor: number) => {
      const svg = svgEl.current;
      const z = behavior.current;
      if (!svg || !z) return;
      if (factor < 1 && zoomTransform(svg).k <= 1.02) {
        if (latest.current.canUp) onUp();
        return;
      }
      gesture.current.pointer = null;
      gesture.current.button = true;
      select(svg)
        .transition()
        .duration(DURATION / 2)
        .call(z.scaleBy, factor);
    },
    [onUp],
  );

  // A projeção é ajustada ao primeiro recorte do país inteiro e mantida entre os
  // níveis, para que a troca de nível não desloque o mapa sob o zoom.
  const [frame] = useState(() => rewindForD3(context ?? collection));
  const byKey = useMemo(() => new Map(values.map((v) => [v.geography_key, v])), [values]);
  const scale = useMemo(() => quantileScale(values.map((v) => v.value)), [values]);
  const path = useMemo(() => {
    const projection = geoMercator().fitExtent(
      [
        [8, 8],
        [size.width - 8, size.height - 8],
      ],
      frame as unknown as GeoJSON.FeatureCollection,
    );
    return geoPath(projection);
  }, [frame, size]);
  const toShapes = useCallback(
    (c: GeoCollection | null): Shape[] =>
      c ? rewindForD3(c).features.map((f) => ({ id: f.id, name: f.properties.name, feature: f, d: path(f) ?? "" })) : [],
    [path],
  );
  const shapes = useMemo(() => toShapes(collection), [toShapes, collection]);
  const contextShapes = useMemo(() => toShapes(context), [toShapes, context]);
  const focusShape = focus ? contextShapes.find((s) => s.id === focus) : undefined;

  // Pedidos de enquadramento (duplo clique, trilha, limpar, recorte vindo da URL).
  // Esperam a geometria do território chegar.
  // Só depois de medir o painel; uma mudança de tamanho refaz o último enquadramento.
  const fitted = useRef("");
  useEffect(() => {
    const id = fitRequest ? `${fitRequest.n}|${size.width}x${size.height}` : "";
    if (!fitRequest || !size.measured || id === fitted.current) return;
    if (fitRequest.key === null) {
      fitted.current = id;
      animate(zoomIdentity);
      return;
    }
    const target = [...shapes, ...contextShapes].find((s) => s.id === fitRequest.key);
    if (!target) return;
    fitted.current = id;
    const view = fitView(path.bounds(target.feature), size.width, size.height);
    animate(zoomIdentity.translate(view.x, view.y).scale(view.k));
  }, [fitRequest, shapes, contextShapes, path, size, animate]);

  // O território selecionado é desenhado por último, para o contorno ficar por cima.
  const ordered = useMemo(
    () => (selected ? [...shapes.filter((p) => p.id !== selected), ...shapes.filter((p) => p.id === selected)] : shapes),
    [shapes, selected],
  );
  const outside = useMemo(() => contextShapes.filter((s) => s.id !== focus), [contextShapes, focus]);
  const hasSuppressed = values.some((v) => v.status === "suppressed");
  const dense = shapes.length > DENSE;

  const handlers = (p: Shape) => ({
    "data-key": p.id,
    tabIndex: 0,
    role: "button",
    "aria-pressed": selected === p.id,
    onMouseMove: (e: React.MouseEvent) => onHover(p.id, p.name, e),
    onFocus: (e: React.FocusEvent<SVGPathElement>) => {
      const r = e.currentTarget.getBoundingClientRect();
      onHover(p.id, p.name, { clientX: r.right, clientY: r.top });
    },
    onBlur: () => onHover(null, "", { clientX: 0, clientY: 0 }),
    onClick: () => onSelect(p.id),
    onDoubleClick: () => onDrill(p.id, "click"),
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onSelect(p.id);
      } else if (e.key === "+") {
        e.preventDefault();
        onDrill(p.id, "click");
      } else if (e.key === "-") {
        e.preventDefault();
        if (canUp) onUp();
      }
    },
  });

  return (
    <div ref={box} className={`map-panel card${dense ? " dense" : ""}`} aria-busy={loading}>
      <svg
        ref={svgEl}
        viewBox={`0 0 ${size.width} ${size.height}`}
        role="img"
        aria-label={label}
        xmlns="http://www.w3.org/2000/svg"
        onMouseMove={(e) => {
          gesture.current.pointer = { x: e.clientX, y: e.clientY };
        }}
        onMouseLeave={(e) => onHover(null, "", e)}
      >
        {hasSuppressed ? (
          <defs>
            <pattern id={HATCH_ID} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="6" height="6" style={{ fill: "var(--odbr-map-missing)" }} />
              <line x1="0" y1="0" x2="0" y2="6" style={{ stroke: "var(--odbr-map-hatch)", strokeWidth: 2 }} />
            </pattern>
          </defs>
        ) : null}
        <rect width={size.width} height={size.height} style={{ fill: CHART.surface }} />
        <g ref={layer}>
          {outside.length ? (
            <g className="map-context">
              {outside.map((p) => (
                <path
                  key={p.id}
                  d={p.d}
                  className={`territory context${selected === p.id ? " selected" : ""}`}
                  aria-label={`${p.name} (${t("focus.outside").toLowerCase()})`}
                  {...handlers(p)}
                />
              ))}
            </g>
          ) : null}
          <g className="map-focus">
            {ordered.map((p) => {
              const value = byKey.get(p.id);
              const fill = value?.status === "suppressed" ? `url(#${HATCH_ID})` : scale.color(value?.value);
              const text =
                value?.value === null || value?.value === undefined
                  ? formatValue(null, value?.status ?? "absent")
                  : formatCompact(value.value);
              return (
                <path
                  key={p.id}
                  d={p.d}
                  className={`territory${selected === p.id ? " selected" : ""}`}
                  style={{ fill }}
                  aria-label={`${p.name}: ${text}`}
                  {...handlers(p)}
                />
              );
            })}
          </g>
          {focusShape ? <path className="focus-outline" d={focusShape.d} aria-hidden="true" /> : null}
        </g>
      </svg>
      {children}
      <div className="map-zoom" role="group" aria-label={t("zoom.group")}>
        <button type="button" onClick={() => zoomBy(STEP)} aria-label={t("zoom.in")} title={t("zoom.in")}>
          +
        </button>
        <button type="button" onClick={() => zoomBy(1 / STEP)} aria-label={t("zoom.out")} title={t("zoom.out")}>
          −
        </button>
        <button
          type="button"
          onClick={() => {
            animate(zoomIdentity);
            onReset();
          }}
          aria-label={t("zoom.reset")}
          title={t("zoom.reset")}
        >
          ⤢
        </button>
      </div>
      {loading ? (
        <p className="map-loading" role="status">
          {t("loading")}
        </p>
      ) : null}
      {scale.breaks.length ? (
        <div className="legend" aria-label="Legenda">
          <ol>
            {scale.breaks.map((b) => (
              <li key={b.color}>
                <i style={{ background: b.color }} />
                {b.from === b.to ? formatCompact(b.from) : `${formatCompact(b.from)} – ${formatCompact(b.to)}`}
              </li>
            ))}
            {hasSuppressed ? (
              <li>
                <i style={{ background: "repeating-linear-gradient(45deg, var(--odbr-map-missing) 0 3px, var(--odbr-map-hatch) 3px 5px)" }} />
                {formatValue(null, "suppressed")}
              </li>
            ) : null}
            {outside.length ? (
              <li>
                <i style={{ background: "var(--odbr-map-context)" }} />
                {t("focus.outside")}
              </li>
            ) : null}
          </ol>
        </div>
      ) : null}
      <p className="map-hint">{t("hoverHint")}</p>
    </div>
  );
});
