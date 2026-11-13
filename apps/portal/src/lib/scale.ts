// Escala de cor do mapa: 7 grupos por quantis (ADR-0009), com limites "redondos".
//
// 1. Quantis: cada grupo tem aproximadamente o mesmo número de territórios, o que
//    evita que São Paulo e as capitais apaguem o resto do mapa. São calculados com
//    os territórios do recorte exibido (a escala se adapta à localidade).
// 2. Limites redondos (DS 2.3.6): cada corte vira o número mais redondo DENTRO da
//    janela entre os quantis vizinhos (do meio do anterior ao meio do seguinte). Com
//    dados espalhados (municípios de 1 mil a 12 milhões), os cortes ficam grossos
//    (4 mil, 10 mil, 25 mil); com dados concentrados (esperança de vida de 72 a 80
//    anos), finos (73,5; 74; 75), sem colapsar em "Até 80 · Mais de 80". Grupos que
//    ficarem vazios são fundidos. Contagens só têm limites inteiros.
// 3. Leitura: o primeiro grupo é "Até X" (≤ X), os do meio "X – Y" (> X e ≤ Y) e o
//    último "Mais de Y". Ex.: Até 4 mil · 4 mil – 5 mil · … · Mais de 15 mil.
// Zero vira um grupo próprio quando é comum (ex.: municípios sem pessoas quilombolas).
// Cores do Design System ODBr (src/lib/theme.ts); com menos grupos, as mais escuras.
import { quantileSorted } from "d3-array";

import { MISSING_COLOR as THEME_MISSING, SEQ, ZERO_COLOR as THEME_ZERO } from "./theme";

export const CLASSES = 7;
export const MISSING_COLOR = THEME_MISSING;
export const ZERO_COLOR = THEME_ZERO;

/** Grupo da legenda. `from`/`to` são os limites redondos (ou o mínimo/máximo nas pontas). */
export interface Break {
  kind: "zero" | "first" | "middle" | "last" | "single";
  from: number;
  to: number;
  color: string;
}

export interface ColorScale {
  color: (value: number | null | undefined) => string;
  breaks: Break[];
}

const NICE = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9];

/** Números redondos em torno de `x` (década de x e a seguinte), em ordem crescente. */
function candidates(x: number, integers: boolean): number[] {
  const decade = 10 ** Math.floor(Math.log10(x));
  const out = [...NICE.map((n) => n * decade), ...NICE.map((n) => n * decade * 10)].map((v) => Number(v.toPrecision(6)));
  return integers ? out.filter((v) => Number.isInteger(v) && v >= 1) : out;
}

/** Número redondo mais próximo de `x` (no empate, o menor). */
export function snapNice(x: number, integers = false): number {
  if (!(x > 0)) return integers ? Math.round(x) : x;
  const options = candidates(x, integers);
  if (!options.length) return integers ? Math.max(1, Math.round(x)) : x;
  return options.reduce((best, v) => (Math.abs(v - x) < Math.abs(best - x) ? v : best));
}

/** Menor número redondo estritamente maior que `x`. */
export function nextNice(x: number, integers = false): number {
  if (!(x > 0)) return integers ? 1 : NICE[0] as number;
  return candidates(x, integers).find((v) => v > x) ?? x * 10;
}

// Passos tentados em cada década, do mais redondo ao mais fino.
const STEPS = [5, 2.5, 2, 1];

/**
 * Número mais redondo em (lo, hi], o mais perto de `target`; undefined se não houver.
 * Desce de década em década; na primeira que tiver candidatos, escolhe entre todos os
 * passos dela o mais perto do quantil (20 em vez de 25 para um quantil de 20,7).
 */
export function roundestIn(lo: number, hi: number, target: number, integers: boolean): number | undefined {
  if (!(hi > lo)) return undefined;
  const top = Math.ceil(Math.log10(Math.max(Math.abs(hi), Math.abs(lo), hi - lo)));
  for (let e = top; e >= top - 12; e--) {
    const found: number[] = [];
    for (const s of STEPS) {
      const step = Number((s * 10 ** e).toPrecision(12));
      if (integers && !(Number.isInteger(step) && step >= 1)) continue;
      const first = Math.floor(lo / step) + 1;
      const last = Math.floor(hi / step);
      if (first > last) continue;
      const k = Math.min(last, Math.max(first, Math.round(target / step)));
      found.push(Number((k * step).toPrecision(12)));
    }
    if (found.length) return found.reduce((a, b) => (Math.abs(b - target) < Math.abs(a - target) ? b : a));
  }
  return undefined;
}

/** Cortes redondos a partir dos quantis; cada grupo resultante tem ao menos um valor. */
export function niceCuts(ranked: number[], classes: number, integers: boolean): number[] {
  if (ranked.length < 2) return [];
  const min = ranked[0] as number;
  const max = ranked[ranked.length - 1] as number;
  const qs = Array.from({ length: classes - 1 }, (_, i) => quantileSorted(ranked, (i + 1) / classes) ?? max);
  const cuts: number[] = [];
  qs.forEach((q, i) => {
    const prev = cuts.at(-1);
    const below = i === 0 ? min : ((qs[i - 1] as number) + q) / 2;
    const above = i === qs.length - 1 ? max : (q + (qs[i + 1] as number)) / 2;
    // "Até X" precisa de valores ≤ X; "Mais de Y" precisa de valores > Y: X em [min, max).
    // Janela inclusiva embaixo (o corte pode ser o próprio mínimo: "Até 1").
    const lo = Math.max(below - (Math.abs(below) * 1e-12 + 1e-12), prev ?? -Infinity);
    const hi = Math.min(above, max);
    const cut = roundestIn(lo, hi, q, integers);
    if (cut === undefined || cut < min || cut >= max || (prev !== undefined && cut <= prev)) return;
    cuts.push(cut);
  });
  // Funde grupos vazios (um corte sem valores entre ele e o anterior).
  return cuts.filter((cut, i) => {
    const lower = i === 0 ? -Infinity : (cuts[i - 1] as number);
    return ranked.some((v) => v > lower && v <= cut);
  });
}

export function quantileScale(values: readonly (number | null | undefined)[]): ColorScale {
  const valid = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (valid.length === 0) return { color: () => MISSING_COLOR, breaks: [] };
  const zeros = valid.filter((v) => v === 0).length;
  const zeroClass = zeros > 0 && zeros / valid.length >= 1 / CLASSES;
  const ranked = (zeroClass ? valid.filter((v) => v !== 0) : valid).sort((a, b) => a - b);
  const classes = zeroClass ? CLASSES - 1 : CLASSES;
  const breaks: Break[] = zeroClass ? [{ kind: "zero", from: 0, to: 0, color: ZERO_COLOR }] : [];
  // Contagens: limites inteiros (não existe "56,33 pessoas").
  const integers = ranked.every((v) => Number.isInteger(v));
  const cuts = niceCuts(ranked, classes, integers);
  if (ranked.length) {
    const min = ranked[0] as number;
    const max = ranked[ranked.length - 1] as number;
    const colors = SEQ.slice(SEQ.length - (cuts.length + 1));
    const color = (i: number) => colors[i] ?? (SEQ[SEQ.length - 1] as string);
    if (!cuts.length) {
      breaks.push({ kind: "single", from: min, to: max, color: color(0) });
    } else {
      breaks.push({ kind: "first", from: min, to: cuts[0] as number, color: color(0) });
      for (let i = 1; i < cuts.length; i++) {
        breaks.push({ kind: "middle", from: cuts[i - 1] as number, to: cuts[i] as number, color: color(i) });
      }
      breaks.push({ kind: "last", from: cuts.at(-1) as number, to: max, color: color(cuts.length) });
    }
  }
  const ranges = breaks.filter((b) => b.kind !== "zero");
  const colorOf = (value: number | null | undefined): string => {
    if (typeof value !== "number" || !Number.isFinite(value)) return MISSING_COLOR;
    if (zeroClass && value === 0) return ZERO_COLOR;
    const found = ranges.find((b) => b.kind !== "last" && value <= b.to);
    return (found ?? ranges.at(-1))?.color ?? MISSING_COLOR;
  };
  return { color: colorOf, breaks };
}
