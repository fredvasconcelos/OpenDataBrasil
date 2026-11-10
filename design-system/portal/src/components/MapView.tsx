"use client";

import { geoMercator, geoPath } from "d3-geo";
import { useTranslations } from "next-intl";
import { forwardRef, useEffect, useMemo, useRef, useState } from "react";

import { formatCompact, formatValue } from "@/lib/format";
import { rewindForD3 } from "@/lib/geo";
import { quantileScale } from "@/lib/scale";
import { CHART } from "@/lib/theme";
import type { GeoCollection, MapValue } from "@/lib/types";

interface Props {
  collection: GeoCollection;
  values: MapValue[];
  selected: string | null;
  onHover: (key: string | null, name: string, event: { clientX: number; clientY: number }) => void;
  onSelect: (key: string) => void;
  label: string;
}

// Acima disso o contorno fica mais fino (municípios: 5.570 polígonos).
const DENSE = 500;
const HATCH_ID = "odbr-hatch";

// Mapa coroplético em SVG: d3 calcula projeção, caminhos e cores; o React desenha.
// Design System ODBr: cores por var(--odbr-…) aplicadas em `style` (var() não funciona
// em atributos de apresentação do SVG); contorno, hover, seleção e foco no globals.css.
export const MapView = forwardRef<SVGSVGElement, Props>(function MapView(
  { collection, values, selected, onHover, onSelect, label },
  ref,
) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 480 });

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setSize({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const byKey = useMemo(() => new Map(values.map((v) => [v.geography_key, v])), [values]);
  const scale = useMemo(() => quantileScale(values.map((v) => v.value)), [values]);
  const sphere = useMemo(() => rewindForD3(collection), [collection]);
  const paths = useMemo(() => {
    const projection = geoMercator().fitExtent(
      [
        [8, 8],
        [size.width - 8, size.height - 8],
      ],
      sphere as unknown as GeoJSON.FeatureCollection,
    );
    const path = geoPath(projection);
    return sphere.features.map((f) => ({ id: f.id, name: f.properties.name, d: path(f) ?? "" }));
  }, [sphere, size]);

  // O território selecionado é desenhado por último, para o contorno ficar por cima.
  const ordered = useMemo(
    () => (selected ? [...paths.filter((p) => p.id !== selected), ...paths.filter((p) => p.id === selected)] : paths),
    [paths, selected],
  );
  const hasSuppressed = values.some((v) => v.status === "suppressed");
  const dense = paths.length > DENSE;

  return (
    <div ref={box} className={`map-panel card${dense ? " dense" : ""}`} style={{ padding: 0 }}>
      <svg
        ref={ref}
        viewBox={`0 0 ${size.width} ${size.height}`}
        role="img"
        aria-label={label}
        xmlns="http://www.w3.org/2000/svg"
        onMouseLeave={(e) => onHover(null, "", e)}
      >
        <title>{label}</title>
        {hasSuppressed ? (
          <defs>
            <pattern id={HATCH_ID} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="6" height="6" style={{ fill: "var(--odbr-map-missing)" }} />
              <line x1="0" y1="0" x2="0" y2="6" style={{ stroke: "var(--odbr-map-hatch)", strokeWidth: 2 }} />
            </pattern>
          </defs>
        ) : null}
        <rect width={size.width} height={size.height} style={{ fill: CHART.surface }} />
        {ordered.map((p) => {
          const value = byKey.get(p.id);
          const fill = value?.status === "suppressed" ? `url(#${HATCH_ID})` : scale.color(value?.value);
          const text = value?.value === null || value?.value === undefined ? formatValue(null, value?.status ?? "absent") : formatCompact(value.value);
          return (
            <path
              key={p.id}
              d={p.d}
              className={`territory${selected === p.id ? " selected" : ""}`}
              style={{ fill }}
              tabIndex={0}
              role="button"
              aria-label={`${p.name}: ${text}`}
              aria-pressed={selected === p.id}
              onMouseMove={(e) => onHover(p.id, p.name, e)}
              onFocus={(e) => {
                const r = e.currentTarget.getBoundingClientRect();
                onHover(p.id, p.name, { clientX: r.right, clientY: r.top });
              }}
              onBlur={(e) => onHover(null, "", e as unknown as { clientX: number; clientY: number })}
              onClick={() => onSelect(p.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(p.id);
                }
              }}
            />
          );
        })}
      </svg>
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
          </ol>
        </div>
      ) : null}
      <p className="map-hint">{t("hoverHint")}</p>
    </div>
  );
});
