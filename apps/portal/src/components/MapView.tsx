"use client";

import { geoMercator, geoPath } from "d3-geo";
import { useTranslations } from "next-intl";
import { forwardRef, useEffect, useMemo, useRef, useState } from "react";

import { formatCompact } from "@/lib/format";
import { rewindForD3 } from "@/lib/geo";
import { quantileScale } from "@/lib/scale";
import type { GeoCollection, MapValue } from "@/lib/types";

interface Props {
  collection: GeoCollection;
  values: MapValue[];
  selected: string | null;
  onHover: (key: string | null, name: string, event: { clientX: number; clientY: number }) => void;
  onSelect: (key: string) => void;
  label: string;
}

// Mapa coroplético em SVG: d3 calcula projeção, caminhos e cores; o React desenha.
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

  return (
    <div ref={box} className="map-panel card" style={{ padding: 0 }}>
      <svg
        ref={ref}
        viewBox={`0 0 ${size.width} ${size.height}`}
        role="img"
        aria-label={label}
        xmlns="http://www.w3.org/2000/svg"
        onMouseLeave={(e) => onHover(null, "", e)}
      >
        <title>{label}</title>
        <rect width={size.width} height={size.height} fill="#ffffff" />
        {paths.map((p) => {
          const value = byKey.get(p.id);
          return (
            <path
              key={p.id}
              d={p.d}
              className={`territory${selected === p.id ? " selected" : ""}`}
              fill={scale.color(value?.value)}
              tabIndex={0}
              role="button"
              aria-label={`${p.name}: ${formatCompact(value?.value)}`}
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
          </ol>
        </div>
      ) : null}
      <p className="muted small" style={{ position: "absolute", right: 12, bottom: 4, margin: 0 }}>
        {t("hoverHint")}
      </p>
    </div>
  );
});
