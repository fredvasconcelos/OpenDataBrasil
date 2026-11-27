import { expect, type Locator, type Page } from "@playwright/test";

// Auxiliares dos testes ponta a ponta (DS 2.9).

/** Abre a árvore do Período (recolhida por padrão na barra lateral) e devolve o grupo. */
export async function openPeriods(page: Page) {
  const summary = page.locator(".sidebar .period-summary");
  if ((await summary.getAttribute("aria-expanded")) === "false") await summary.click();
  return page.getByRole("group", { name: "Período", exact: true });
}

/** Abre o painel "Escolher indicador" e devolve o diálogo. */
export async function openCatalog(page: Page) {
  await page.getByRole("button", { name: "Trocar indicador" }).click();
  return page.getByRole("dialog", { name: "Escolher indicador" });
}


/** Só o círculo do SVG recebe o fundo; nenhuma camada HTML desenha outro halo. */
export async function expectCompactInfo(button: Locator) {
  const appearance = await button.evaluate(el => {
    const svg = el.querySelector("svg")!, disc = svg.querySelector("circle[stroke]")!;
    const icon = svg.getBoundingClientRect(), control = el.getBoundingClientRect();
    const layers = [el, ...el.querySelectorAll("*")].filter(n => n instanceof HTMLElement)
      .map(n => {
        const css = getComputedStyle(n);
        return { background: css.backgroundColor, border: css.borderTopWidth, shadow: css.boxShadow };
      });
    return { layers, width: icon.width, height: icon.height,
      within: icon.left >= control.left && icon.right <= control.right
        && icon.top >= control.top && icon.bottom <= control.bottom,
      dx: control.x + control.width / 2 - icon.x - icon.width / 2,
      dy: control.y + control.height / 2 - icon.y - icon.height / 2,
      fill: getComputedStyle(disc).fill, stroke: getComputedStyle(disc).stroke };
  });
  expect(appearance.layers.length).toBeGreaterThan(0);
  for (const layer of appearance.layers) {
    expect(layer).toEqual({ background: "rgba(0, 0, 0, 0)", shadow: "none", border: "0px" });
  }
  expect(appearance.width).toBeGreaterThanOrEqual(18);
  expect(Math.abs(appearance.width - appearance.height)).toBeLessThan(0.5);
  expect(appearance.within).toBe(true);
  expect(Math.abs(appearance.dx)).toBeLessThan(0.5);
  expect(Math.abs(appearance.dy)).toBeLessThan(0.5);
  expect(appearance.fill).not.toMatch(/^(none|transparent|rgba\(0, 0, 0, 0\))$/);
  expect(appearance.stroke).not.toBe("none");
}
