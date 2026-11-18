"use client";

import "flag-icons/css/flag-icons.min.css";

import { geoCentroid, geoDistance, geoGraticule10, geoMercator, geoOrthographic, geoPath, type GeoPermissibleObjects } from "d3-geo";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import world from "world-atlas/countries-110m.json";

import { AccessTooltip } from "@/components/AccessTooltip";
import { useValueLabels } from "@/components/useValueLabels";
import { ISO_NUMERIC_TO_ALPHA2 } from "@/lib/iso3166";
import { geoColors, REGIONS, regionOfUf, viewsText, type GeoItem, type GeoLevel } from "@/lib/metrics";
import { MISSING_COLOR } from "@/lib/theme";
import type { GeoCollection, GeoFeature } from "@/lib/types";

interface Props {
  level: GeoLevel;
  items: readonly GeoItem[];
  /** Geometria do release (Grandes Regiões e UFs); só nos níveis do Brasil. */
  regions: GeoCollection | null;
  ufs: GeoCollection | null;
  /** No nível Estado: "pais:BR" (todas) ou "regiao:N" (recorte). */
  within: string | null;
  selected: string | null;
  /** Período por extenso, no tooltip. */
  period: string;
  onActivate: (key: string) => void;
}

const W = 800;
const H = 500;
// Globo centrado no Brasil (DS 2.12): rotate [52, 14].
const START: [number, number] = [52, 14];
const ZOOM_STEP = 1.4;
const MAX_K = 4;

type WorldFeature = GeoJSON.Feature<GeoJSON.Geometry, { name: string }> & { id?: string };

// Países da geometria do world-atlas (Natural Earth 110m), com a sigla ISO alfa-2.
const COUNTRIES: { a2: string | null; feature: WorldFeature }[] = (() => {
  const topo = world as unknown as Topology<{ countries: GeometryCollection<{ name: string }> }>;
  const fc = feature(topo, topo.objects.countries) as GeoJSON.FeatureCollection<GeoJSON.Geometry, { name: string }>;
  return fc.features.map((f) => {
    const id = (f as WorldFeature).id;
    return { a2: id ? (ISO_NUMERIC_TO_ALPHA2[String(id)] ?? null) : null, feature: f as WorldFeature };
  });
})();

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

interface Point {
  item: GeoItem;
  x: number;
  y: number;
  /** Conteúdo do ponto: bandeira de país, bandeira de UF ou sigla da região. */
  kind: "country" | "uf" | "region";
  code: string;
}

// Mapa de acessos (DS 2.12, ADR-0027). d3-geo calcula projeção e caminhos; o React desenha
// o SVG e põe os pontos como <button> por cima (foco, Enter e aria-label). Sem mapa de fundo
// e sem requisição a terceiros. As cores são var(--odbr-…), então o tema escuro troca sozinho.
// - País: globo ortográfico; arrastar gira; a rotação automática lenta para na primeira
//   interação e não roda com prefers-reduced-motion. Brasil em destaque; pontos com bandeira.
// - Grande Região e Estado: coroplético por quantis (lib/scale), zero em --odbr-map-zero,
//   selecionado 2,5px em --odbr-map-selected e o recorte da região em --odbr-map-focus.
export function AccessMap({ level, items, regions, ufs, within, selected, period, onActivate }: Props) {
  const t = useTranslations("metrics.map");
  const labels = useValueLabels();
  const [rotate, setRotate] = useState<[number, number]>(START);
  const [k, setK] = useState(1);
  const [pan, setPan] = useState<[number, number]>([0, 0]);
  const [still, setStill] = useState(() => prefersReducedMotion());
  const [hover, setHover] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; rotate: [number, number]; pan: [number, number] } | null>(null);

  // Nova visão a cada troca de nível ou recorte (ajuste durante a renderização).
  const view = `${level}|${within ?? ""}`;
  const [seenView, setSeenView] = useState(view);
  if (seenView !== view) {
    setSeenView(view);
    setK(1);
    setPan([0, 0]);
  }

  // Rotação automática lenta do globo, até a primeira interação.
  useEffect(() => {
    if (level !== "pais" || still) return;
    let frame = 0;
    const tick = () => {
      setRotate(([lon, lat]) => [(lon + 0.06) % 360, lat]);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [level, still]);

  const byKey = useMemo(() => new Map(items.map((i) => [i.geography_key, i])), [items]);
  const colors = useMemo(() => geoColors(items), [items]);

  const brazilFeatures = useMemo<GeoFeature[]>(() => {
    if (level === "regiao") return regions?.features ?? [];
    if (level === "uf") {
      const all = ufs?.features ?? [];
      return within?.startsWith("regiao:") ? all.filter((f) => regionOfUf(f.id) === within) : all;
    }
    return [];
  }, [level, regions, ufs, within]);

  const projection = useMemo(() => {
    if (level === "pais") {
      return geoOrthographic()
        .scale(230 * k)
        .translate([W / 2, H / 2])
        .rotate([rotate[0], rotate[1]])
        .clipAngle(90);
    }
    if (!brazilFeatures.length) return null;
    const fc = { type: "FeatureCollection", features: brazilFeatures } as unknown as GeoPermissibleObjects;
    return geoMercator().fitExtent(
      [
        [24, 24],
        [W - 24, H - 24],
      ],
      fc,
    );
  }, [level, k, rotate, brazilFeatures]);

  const path = useMemo(() => (projection ? geoPath(projection) : null), [projection]);
  // No Brasil, o zoom e o arraste são uma transformação do <g> (os caminhos não mudam).
  const transform = level === "pais" ? "" : `translate(${pan[0] + (W / 2) * (1 - k)} ${pan[1] + (H / 2) * (1 - k)}) scale(${k})`;
  const place = (x: number, y: number): [number, number] =>
    level === "pais" ? [x, y] : [pan[0] + (W / 2) * (1 - k) + x * k, pan[1] + (H / 2) * (1 - k) + y * k];

  const points = useMemo<Point[]>(() => {
    if (!projection || !path) return [];
    const out: Point[] = [];
    if (level === "pais") {
      const center: [number, number] = [-rotate[0], -rotate[1]];
      for (const { a2, feature: f } of COUNTRIES) {
        const item = a2 ? byKey.get(`pais:${a2}`) : undefined;
        if (!item || !a2) continue;
        const c = geoCentroid(f);
        if (geoDistance(c, center) > Math.PI / 2 - 0.08) continue; // atrás do globo
        const xy = projection(c);
        if (xy) out.push({ item, x: xy[0], y: xy[1], kind: "country", code: a2.toLowerCase() });
      }
    } else {
      for (const f of brazilFeatures) {
        const item = byKey.get(f.id);
        if (!item) continue;
        const [x, y] = path.centroid(f as unknown as GeoPermissibleObjects);
        if (!Number.isFinite(x)) continue;
        const [px, py] = place(x, y);
        const code = level === "uf" ? (f.properties.uf ?? "").toLowerCase() : (REGIONS[f.id]?.abbr ?? "");
        out.push({ item, x: px, y: py, kind: level === "uf" ? "uf" : "region", code });
      }
    }
    // Ordem do Tab: mais acessados primeiro.
    return out.sort((a, b) => (b.item.views ?? 0) - (a.item.views ?? 0));
    // `place` depende só de pan e k, já listados.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projection, path, level, brazilFeatures, byKey, rotate, pan, k]);

  const stop = () => setStill(true);
  const zoom = (factor: number) => {
    stop();
    setK((v) => Math.min(MAX_K, Math.max(1, v * factor)));
    if (factor < 1) setPan(([x, y]) => [x / ZOOM_STEP, y / ZOOM_STEP]);
  };
  const reset = () => {
    stop();
    setK(1);
    setPan([0, 0]);
    setRotate(START);
  };

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    stop();
    drag.current = { x: e.clientX, y: e.clientY, rotate, pan };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (!d) return;
    const box = e.currentTarget.getBoundingClientRect();
    const scale = box.width ? W / box.width : 1;
    const dx = (e.clientX - d.x) * scale;
    const dy = (e.clientY - d.y) * scale;
    if (level === "pais") {
      setRotate([d.rotate[0] + dx * 0.25, Math.max(-70, Math.min(70, d.rotate[1] - dy * 0.25))]);
    } else if (k > 1) {
      setPan([d.pan[0] + dx, d.pan[1] + dy]);
    }
  };
  const onPointerUp = () => {
    drag.current = null;
  };

  const tipItem = hover ? byKey.get(hover) : undefined;
  const tipPoint = hover ? points.find((p) => p.item.geography_key === hover) : undefined;
  const valueLabel = (item: GeoItem) => (item.status === "ok" ? `${viewsText(item, labels)} ${t("views")}` : viewsText(item, labels));

  const outline = level === "uf" && within?.startsWith("regiao:") ? regions?.features.find((f) => f.id === within) : undefined;
  const ordered = selected ? [...brazilFeatures].sort((a, b) => Number(a.id === selected) - Number(b.id === selected)) : brazilFeatures;

  return (
    <div className="access-map">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={t("title")}
        className={level === "pais" ? "is-globe" : undefined}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        {path && level === "pais" ? (
          <g>
            <path d={path({ type: "Sphere" }) ?? ""} fill="var(--odbr-bg-selected)" stroke="var(--odbr-border)" />
            <path d={path(geoGraticule10()) ?? ""} fill="none" stroke="var(--odbr-border)" strokeWidth={0.5} />
            {COUNTRIES.map(({ a2, feature: f }, i) => (
              <path
                key={a2 ?? `sem-codigo-${i}`}
                d={path(f) ?? ""}
                fill={a2 === "BR" ? "var(--odbr-primary)" : "var(--odbr-map-context)"}
                fillOpacity={a2 === "BR" ? 0.22 : 1}
                stroke={a2 === "BR" ? "var(--odbr-map-focus)" : "var(--odbr-map-context-stroke)"}
                strokeWidth={a2 === "BR" ? 1.5 : 0.5}
              />
            ))}
          </g>
        ) : null}
        {path && level !== "pais" ? (
          <g transform={transform}>
            {ordered.map((f) => {
              const item = byKey.get(f.id);
              const isSel = f.id === selected;
              return (
                <path
                  key={f.id}
                  d={path(f as unknown as GeoPermissibleObjects) ?? ""}
                  fill={item ? colors.color(item) : MISSING_COLOR}
                  stroke={isSel ? "var(--odbr-map-selected)" : "var(--odbr-map-stroke)"}
                  strokeWidth={(isSel ? 2.5 : 0.6) / k}
                  onClick={() => onActivate(f.id)}
                />
              );
            })}
            {outline ? (
              <path d={path(outline as unknown as GeoPermissibleObjects) ?? ""} fill="none" stroke="var(--odbr-map-focus)" strokeWidth={2 / k} pointerEvents="none" />
            ) : null}
          </g>
        ) : null}
      </svg>
      {points.map((p) => (
        <button
          key={p.item.geography_key}
          type="button"
          className={`access-point access-point-${p.kind}${p.item.geography_key === selected ? " is-active" : ""}`}
          style={{ left: `${(p.x / W) * 100}%`, top: `${(p.y / H) * 100}%` }}
          aria-label={t("point", { name: p.item.name, value: valueLabel(p.item) })}
          aria-pressed={p.item.geography_key === selected}
          onMouseEnter={() => setHover(p.item.geography_key)}
          onMouseLeave={() => setHover(null)}
          onFocus={() => {
            stop();
            setHover(p.item.geography_key);
          }}
          onBlur={() => setHover(null)}
          onClick={() => onActivate(p.item.geography_key)}
        >
          {p.kind === "country" ? <span className={`fi fi-${p.code} fis`} aria-hidden="true" /> : null}
          {p.kind === "uf" && p.code ? (
            // eslint-disable-next-line @next/next/no-img-element -- bandeira estática em public/ (CC0)
            <img src={`/bandeiras-uf/${p.code}.svg`} alt="" width={28} height={28} />
          ) : null}
          {p.kind === "region" ? <span aria-hidden="true">{p.code}</span> : null}
        </button>
      ))}
      {tipItem && tipPoint ? (
        <AccessTooltip item={tipItem} period={period} x={`${(tipPoint.x / W) * 100}%`} y={`${(tipPoint.y / H) * 100}%`} />
      ) : null}
      <div className="map-zoom access-zoom" role="group" aria-label={t("controls")}>
        <button type="button" onClick={() => zoom(ZOOM_STEP)} aria-label={t("zoomIn")} title={t("zoomIn")} disabled={k >= MAX_K}>
          +
        </button>
        <button type="button" onClick={() => zoom(1 / ZOOM_STEP)} aria-label={t("zoomOut")} title={t("zoomOut")} disabled={k <= 1}>
          −
        </button>
        <button type="button" onClick={reset} aria-label={t("reset")} title={t("reset")}>
          ⟲
        </button>
      </div>
      {level !== "pais" ? (
        <div className="access-legend" aria-label={t("legend")} role="group">
          <span className="access-legend-scale">
            <span>{t("less")}</span>
            {colors.scale.breaks.map((b, i) => (
              <span key={i} className="access-swatch" style={{ background: b.color }} aria-hidden="true" />
            ))}
            <span>{t("more")}</span>
          </span>
          <span className="access-legend-item">
            <span className="access-swatch" style={{ background: "var(--odbr-seq-1)" }} aria-hidden="true" />
            {labels.lessThan}
          </span>
          <span className="access-legend-item">
            <span className="access-swatch" style={{ background: "var(--odbr-map-zero)" }} aria-hidden="true" />
            {labels.noAccess}
          </span>
        </div>
      ) : null}
      <p className="access-attribution">{t("attribution")}</p>
    </div>
  );
}
