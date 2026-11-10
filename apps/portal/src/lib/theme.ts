// Cores de dados do Design System ODBr como variáveis CSS (src/styles/tokens.css).
// Por serem var(--…), trocam sozinhas com o tema, sem recalcular o d3.
// Atenção: em SVG, var() só funciona em `style` (style={{ fill }}), não em
// atributos de apresentação (fill="…"). Na exportação, use resolveSvgColors().

export const SEQ: readonly string[] = Array.from({ length: 7 }, (_, i) => `var(--odbr-seq-${i + 1})`);
export const SERIES: readonly string[] = Array.from({ length: 10 }, (_, i) => `var(--odbr-series-${i + 1})`);
export const ZERO_COLOR = "var(--odbr-map-zero)";
export const MISSING_COLOR = "var(--odbr-map-missing)";

export const CHART = {
  grid: "var(--odbr-chart-grid)",
  axis: "var(--odbr-chart-axis)",
  label: "var(--odbr-chart-label)",
  highlight: "var(--odbr-chart-highlight)",
  surface: "var(--odbr-bg-surface)",
} as const;

export type ThemeName = "light" | "dark";
export const THEME_STORAGE_KEY = "odbr-theme";

/** Lê um token já resolvido (ex.: "--odbr-bg-surface" → "#FFFFFF"). */
export function token(name: string, fallback = ""): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

const PAINT_PROPS = ["fill", "stroke", "stroke-width", "opacity", "fill-opacity", "stroke-opacity"] as const;
const TEXT_PROPS = ["font-family", "font-size", "font-weight"] as const;

/**
 * Copia para o clone as cores calculadas no SVG original. Sem isso o arquivo
 * exportado perde tudo o que vem de var(--…) e das classes do globals.css.
 * `original` e `clone` precisam ter a mesma estrutura (clone = original.cloneNode(true)).
 */
export function resolveSvgColors(original: SVGSVGElement, clone: SVGSVGElement): void {
  const src = [original, ...Array.from(original.querySelectorAll<SVGElement>("*"))];
  const dst = [clone, ...Array.from(clone.querySelectorAll<SVGElement>("*"))];
  src.forEach((el, i) => {
    const target = dst[i];
    if (!target) return;
    const cs = getComputedStyle(el);
    for (const prop of PAINT_PROPS) target.style.setProperty(prop, cs.getPropertyValue(prop));
    if (el.tagName.toLowerCase() === "text") {
      for (const prop of TEXT_PROPS) target.style.setProperty(prop, cs.getPropertyValue(prop));
    }
  });
}
