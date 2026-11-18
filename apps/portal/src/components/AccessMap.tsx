"use client";

import "flag-icons/css/flag-icons.min.css";

import { geoCentroid, geoDistance, geoGraticule10, geoOrthographic, geoPath, type GeoPermissibleObjects } from "d3-geo";
import { useTranslations } from "next-intl";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
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
  stateItems?: readonly GeoItem[];
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
const MAX_K = 8;

/** Preserva a posição sob o cursor e recentra progressivamente ao afastar. */
function anchoredOffset(previous: number, next: number, offset: [number, number], anchor: [number, number]): [number, number] {
  if (next === 1) return [0, 0];
  const limit = 230 * (next - 1);
  return anchor.map((value, index) => Math.max(-limit, Math.min(limit,
    value - (value - (offset[index] ?? 0)) * next / previous))) as [number, number];
}

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
// - País: globo ortográfico parado; arraste esquerdo gira e a roda aproxima.
//   Ao aproximar do Brasil, aparecem as UFs; nenhuma chamada a mapa externo.
// - Grande Região e Estado: coroplético por quantis (lib/scale), zero em --odbr-map-zero,
//   selecionado 2,5px em --odbr-map-selected e o recorte da região em --odbr-map-focus.
export function AccessMap({ level: requestedLevel, items: countries, stateItems = [], regions, ufs, within, selected, period, onActivate }: Props) {
  const surface = useRef<HTMLDivElement>(null);
  const t = useTranslations("metrics.map");
  const labels = useValueLabels();
  const [rotate, setRotate] = useState<[number, number]>(START);
  const [k, setK] = useState(1);
  const [offset, setOffset] = useState<[number, number]>([0, 0]);
  const camera = useRef({ k, offset });
  useLayoutEffect(() => { camera.current = { k, offset }; }, [k, offset]);
  const previewProjection = geoOrthographic().scale(230 * k)
    .translate([W / 2 + offset[0], H / 2 + offset[1]]).rotate(rotate);
  const brazilPoint = previewProjection([-52, -14]);
  const brazilVisible = !!brazilPoint && geoDistance([-rotate[0], -rotate[1]], [-52, -14]) < Math.PI / 2
    && brazilPoint[0] >= 0 && brazilPoint[0] <= W && brazilPoint[1] >= 0 && brazilPoint[1] <= H;
  const [detailed, setDetailed] = useState(false);
  const nextDetailed = brazilVisible && (detailed ? k >= 2.2 : k >= 2.6);
  if (nextDetailed !== detailed) setDetailed(nextDetailed);
  const level: GeoLevel = requestedLevel !== "pais" ? requestedLevel : detailed ? "uf" : "pais";
  const items = level === "pais" ? countries : stateItems.length ? stateItems : countries;
  const [hover, setHover] = useState<string | null>(null);
  const moved = useRef(false);
  const touches = useRef(new Map<number, [number, number]>());
  const pinch = useRef<{ distance: number; scale: number; offset: [number, number]; anchor: [number, number] } | null>(null);
  const drag = useRef<{ x: number; y: number; rotate: [number, number] } | null>(null);

  useEffect(() => {
    const node = surface.current?.querySelector<HTMLElement>(".access-map-surface");
    if (!node) return;
    const wheel = (e: WheelEvent) => {
      if (e.ctrlKey) return;
      const current = camera.current;
      const delta = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? node.clientHeight : 1);
      const next = Math.max(1, Math.min(MAX_K, current.k * Math.exp(-delta * 0.002)));
      if (next === current.k) return;
      e.preventDefault();
      setHover(null);
      const box = node.getBoundingClientRect();
      const anchor: [number, number] = [(e.clientX - box.left) * W / box.width - W / 2,
        (e.clientY - box.top) * H / box.height - H / 2];
      const nextOffset = anchoredOffset(current.k, next, current.offset, anchor);
      camera.current = { k: next, offset: nextOffset };
      setOffset(nextOffset);
      setK(next);
    };
    node.addEventListener("wheel", wheel, { passive: false });
    return () => node.removeEventListener("wheel", wheel);
  }, []);
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

  const [seenSelection, setSeenSelection] = useState<string | null>(null);
  if (selected !== seenSelection) {
    setSeenSelection(selected);
    const country = COUNTRIES.find(c => `pais:${c.a2}` === selected);
    const territory = ufs?.features.find(f => f.id === selected) ?? regions?.features.find(f => f.id === selected);
    const shape = territory ?? country?.feature;
    if (shape) {
      const [lon, lat] = geoCentroid(shape as GeoPermissibleObjects);
      setRotate([-lon, -lat]);
      setOffset([0, 0]);
      setK(selected?.startsWith("pais:") ? 1 : 3);
      setHover(selected);
    }
  }

  const projection = useMemo(() => {
    return geoOrthographic().scale(230 * k).translate([W / 2 + offset[0], H / 2 + offset[1]])
      .rotate([rotate[0], rotate[1]]).clipAngle(90).clipExtent([[0, 0], [W, H]]);
  }, [k, rotate, offset]);

  const path = useMemo(() => (projection ? geoPath(projection) : null), [projection]);
  const transform = "";
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
        const centroid = geoCentroid(f as unknown as GeoPermissibleObjects);
        if (geoDistance(centroid, [-rotate[0], -rotate[1]]) > Math.PI / 2 - 0.08) continue;
        const xy = projection(centroid);
        if (!xy) continue;
        const [px, py] = xy;
        const code = level === "uf" ? (f.properties.uf ?? "").toLowerCase() : (REGIONS[f.id]?.abbr ?? "");
        out.push({ item, x: px, y: py, kind: level === "uf" ? "uf" : "region", code });
      }
    }
    // Ordem do Tab: mais acessados primeiro.
    return out.filter(p => p.x >= 16 && p.x <= W - 16 && p.y >= 16 && p.y <= H - 16).sort((a, b) => (b.item.views ?? 0) - (a.item.views ?? 0));
  }, [projection, path, level, brazilFeatures, byKey, rotate]);

  const stop = () => setHover(null);
  const zoom = (factor: number) => {
    stop();
    const next = Math.min(MAX_K, Math.max(1, k * factor));
    setOffset(anchoredOffset(k, next, offset, [0, 0]));
    setK(next);
  };
  const reset = () => {
    stop();
    setK(1);
    setOffset([0, 0]);
    setRotate(START);
  };

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    if (e.pointerType === "touch") {
      touches.current.set(e.pointerId, [e.clientX, e.clientY]);
      if (touches.current.size === 2) {
        const [a, b] = [...touches.current.values()];
        if (a && b) {
          const box = surface.current!.querySelector(".access-map-surface")!.getBoundingClientRect();
          pinch.current = { distance: Math.hypot(a[0] - b[0], a[1] - b[1]), scale: k, offset,
            anchor: [((a[0] + b[0]) / 2 - box.left) * W / box.width - W / 2,
              ((a[1] + b[1]) / 2 - box.top) * H / box.height - H / 2] };
        }
      }
    }
    moved.current = false;
    stop();
    drag.current = { x: e.clientX, y: e.clientY, rotate };
    if (!(e.target instanceof Element) || !e.target.closest("button")) e.currentTarget.setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse" && !(e.buttons & 1)) { drag.current = null; return; }
    if (e.pointerType === "touch") {
      touches.current.set(e.pointerId, [e.clientX, e.clientY]);
      const [a, b] = [...touches.current.values()];
      if (pinch.current && a && b && pinch.current.distance > 0) {
        const start = pinch.current;
        const next = Math.max(1, Math.min(MAX_K, start.scale * Math.hypot(a[0] - b[0], a[1] - b[1]) / start.distance));
        setK(next);
        setOffset(anchoredOffset(start.scale, next, start.offset, start.anchor));
        setHover(null);
        moved.current = true;
        return;
      }
    }
    const d = drag.current;
    if (!d) return;
    const box = e.currentTarget.getBoundingClientRect();
    const scale = box.width ? W / box.width : 1;
    if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 4) moved.current = true;
    const dx = (e.clientX - d.x) * scale;
    const dy = (e.clientY - d.y) * scale;
    setRotate([d.rotate[0] + dx * 0.25, Math.max(-70, Math.min(70, d.rotate[1] - dy * 0.25))]);
  };
  const onPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    touches.current.delete(e.pointerId);
    pinch.current = null;
    drag.current = null;
  };

  const tipItem = hover ? byKey.get(hover) : undefined;
  const tipPoint = hover ? points.find((p) => p.item.geography_key === hover) : undefined;
  const valueLabel = (item: GeoItem) => (item.status === "ok" ? `${viewsText(item, labels)} ${t("views")}` : viewsText(item, labels));

  const outline = level === "uf" && within?.startsWith("regiao:") ? regions?.features.find((f) => f.id === within) : undefined;
  const ordered = selected ? [...brazilFeatures].sort((a, b) => Number(a.id === selected) - Number(b.id === selected)) : brazilFeatures;

  return (
    <div className="access-map" ref={surface} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
      <div className="access-map-surface">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={t("title")}
        className={level === "pais" ? "is-globe" : undefined}
        tabIndex={0}
        onKeyDown={e => {
          if (["+", "=", "-", "Home", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) e.preventDefault();
          if (e.key === "+" || e.key === "=") zoom(ZOOM_STEP);
          if (e.key === "-") zoom(1 / ZOOM_STEP);
          if (e.key === "Home") reset();
          if (e.key.startsWith("Arrow")) setRotate(([x, y]) => [x + (e.key === "ArrowLeft" ? -5 : e.key === "ArrowRight" ? 5 : 0), Math.max(-80, Math.min(80, y + (e.key === "ArrowUp" ? 5 : e.key === "ArrowDown" ? -5 : 0)))]);
        }}
      >
        {path ? (
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
          onClick={event => { if (event.detail === 0 || !moved.current) { setHover(p.item.geography_key); onActivate(p.item.geography_key); } }}
        >
          {p.kind === "country" ? <span className={`fi fi-${p.code} fis`} aria-hidden="true" /> : null}
          {p.kind === "uf" && p.code ? (
            // eslint-disable-next-line @next/next/no-img-element -- bandeira estática em public/ (CC0)
            <img src={`/bandeiras-uf/${p.code}.svg`} alt="" draggable={false} />
          ) : null}
          {p.kind === "region" ? <span aria-hidden="true">{p.code}</span> : null}
        </button>
      ))}
      {tipItem && tipPoint ? (
        <AccessTooltip item={tipItem} period={period} x={`${(tipPoint.x / W) * 100}%`} y={`${(tipPoint.y / H) * 100}%`} />
      ) : null}
      </div>
      <p className="access-attribution"><a href="https://d3js.org/">D3</a> · <a href="https://www.naturalearthdata.com/">Natural Earth</a> · <a href="https://www.ibge.gov.br/">IBGE</a></p>
    </div>
  );
}
