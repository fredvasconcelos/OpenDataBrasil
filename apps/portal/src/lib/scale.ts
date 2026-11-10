// Escala de cor por quantis (7 faixas, ADR-0009): cada faixa tem o mesmo número de
// territórios, o que evita que São Paulo e as capitais apaguem o resto do mapa.
// Zero vira uma classe própria quando é comum (por exemplo, municípios sem pessoas
// quilombolas), e limites repetidos são fundidos: nenhuma faixa "0 – 0".
// Design System ODBr: as cores vêm de src/lib/theme.ts (var(--odbr-seq-1..7)),
// no lugar de schemeBlues; com menos faixas, usa as últimas (mais escuras).
import { quantileSorted } from "d3-array";

import { MISSING_COLOR as THEME_MISSING, SEQ, ZERO_COLOR as THEME_ZERO } from "./theme";

export const CLASSES = 7;
export const MISSING_COLOR = THEME_MISSING;
export const ZERO_COLOR = THEME_ZERO;

export interface Break {
  from: number;
  to: number;
  color: string;
}

export interface ColorScale {
  color: (value: number | null | undefined) => string;
  breaks: Break[];
}

export function quantileScale(values: readonly (number | null | undefined)[]): ColorScale {
  const valid = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (valid.length === 0) return { color: () => MISSING_COLOR, breaks: [] };
  const zeros = valid.filter((v) => v === 0).length;
  const zeroClass = zeros > 0 && zeros / valid.length >= 1 / CLASSES;
  const ranked = (zeroClass ? valid.filter((v) => v !== 0) : valid).sort((a, b) => a - b);
  const classes = zeroClass ? CLASSES - 1 : CLASSES;
  const breaks: Break[] = zeroClass ? [{ from: 0, to: 0, color: ZERO_COLOR }] : [];
  if (ranked.length) {
    const min = ranked[0] as number;
    const max = ranked[ranked.length - 1] as number;
    // Contagens: limites inteiros (não existe "56,33 pessoas").
    const integers = ranked.every((v) => Number.isInteger(v));
    const cuts = [min];
    for (let i = 1; i < classes; i++) {
      const raw = quantileSorted(ranked, i / classes) ?? max;
      const q = integers ? Math.round(raw) : raw;
      if (q > (cuts[cuts.length - 1] as number) && q < max) cuts.push(q);
    }
    cuts.push(max);
    const n = Math.max(1, cuts.length - 1);
    const colors = SEQ.slice(SEQ.length - n);
    for (let i = 0; i < n; i++) {
      breaks.push({ from: cuts[i] as number, to: cuts[i + 1] ?? max, color: colors[i] ?? (SEQ[SEQ.length - 1] as string) });
    }
  }
  const color = (value: number | null | undefined): string => {
    if (typeof value !== "number" || !Number.isFinite(value)) return MISSING_COLOR;
    if (zeroClass && value === 0) return ZERO_COLOR;
    const ranges = breaks.filter((b) => b.color !== ZERO_COLOR);
    for (let i = 0; i < ranges.length; i++) {
      const b = ranges[i] as Break;
      if (value < b.to || i === ranges.length - 1) return b.color;
    }
    return MISSING_COLOR;
  };
  return { color, breaks };
}
