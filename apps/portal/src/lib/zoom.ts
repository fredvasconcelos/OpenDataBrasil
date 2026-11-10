// Zoom do mapa com ampliação seletiva (recorte).
//
// O mapa abre nas Grandes Regiões. Aproximar uma região (duplo clique, roda do
// mouse ou botão +) define o **recorte**: só ele se subdivide no nível seguinte
// (UFs da região) e recebe o gradiente; o resto do país continua no nível do
// recorte, em cinza. Aproximar uma UF do recorte leva aos municípios dela.
// Afastar volta ao recorte de cima. Funções puras, sem DOM; o MapView aplica com
// d3-zoom e o painel guarda o recorte na URL (?foco=).

/** Ordem de aprofundamento do mapa. Níveis sem geometria no KPI são pulados. */
export const ZOOM_LADDER = ["regiao", "uf", "municipio"] as const;

/** Ordem geral dos níveis (do mais agregado ao mais detalhado). */
const LEVEL_ORDER = ["brasil", "regiao", "uf", "municipio"];

/** Aproximação máxima (municípios pequenos ainda ficam legíveis). */
export const MAX_SCALE = 80;

/** Aproximar este fator além da escala do recorte atual abre o recorte seguinte. */
export const DRILL_RATIO = 2;

/** Afastar abaixo deste fator da escala do recorte atual volta ao recorte de cima. */
export const UP_RATIO = 0.6;

export interface View {
  k: number;
  x: number;
  y: number;
}

/** Degraus da escada que o KPI tem com mapa, na ordem de aprofundamento. */
export function zoomLadder(mapLevels: readonly string[]): string[] {
  return ZOOM_LADDER.filter((l) => mapLevels.includes(l));
}

/** Nível de uma chave territorial (`uf:29` → `uf`). */
export function levelOf(key: string): string {
  return key.split(":")[0] ?? "";
}

/** `a` é mais agregado que `b` (ex.: regiao antes de uf). */
export function isShallower(a: string, b: string): boolean {
  const i = LEVEL_ORDER.indexOf(a);
  const j = LEVEL_ORDER.indexOf(b);
  return i >= 0 && j >= 0 && i < j;
}

/** Próximo nível ao aprofundar a partir de `level` (null no último degrau). */
export function nextLevel(ladder: readonly string[], level: string): string | null {
  const i = ladder.indexOf(level);
  if (i < 0) return ladder[0] ?? null;
  return ladder[i + 1] ?? null;
}

/** Nível anterior na escada (null no primeiro degrau). */
export function previousLevel(ladder: readonly string[], level: string): string | null {
  const i = ladder.indexOf(level);
  return i > 0 ? (ladder[i - 1] ?? null) : null;
}

/** Um recorte é válido se for de um degrau da escada mais agregado que o nível exibido. */
export function validFocus(ladder: readonly string[], focus: string | null, level: string): boolean {
  if (!focus) return false;
  const fl = levelOf(focus);
  return ladder.includes(fl) && ladder.includes(level) && isShallower(fl, level);
}

export type ZoomDecision = "drill" | "up" | "reset" | null;

/**
 * O que um gesto de zoom do usuário pede, comparando a escala final `k` com a
 * escala `base` em que o recorte atual foi aberto. `canUp`: há recorte ou nível
 * acima para onde voltar.
 */
export function zoomDecision(k: number, base: number, canUp: boolean): ZoomDecision {
  if (canUp && k <= 1.02) return "reset";
  if (k >= base * DRILL_RATIO) return "drill";
  if (canUp && k <= base * UP_RATIO) return "up";
  return null;
}

/**
 * Enquadra um retângulo (coordenadas da projeção base) no centro da tela, com a
 * escala limitada a `range`. Se o território for grande demais para a faixa, o
 * centro dele fica no centro da tela e as bordas podem sair dela.
 */
export function fitView(
  bounds: [[number, number], [number, number]],
  width: number,
  height: number,
  range: [number, number] = [1, MAX_SCALE],
  padding = 0.9,
): View {
  const [[x0, y0], [x1, y1]] = bounds;
  const dx = Math.max(x1 - x0, 1e-6);
  const dy = Math.max(y1 - y0, 1e-6);
  const fit = padding / Math.max(dx / width, dy / height);
  const k = Math.min(Math.max(fit, range[0]), range[1]);
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  return { k, x: width / 2 - k * cx, y: height / 2 - k * cy };
}
