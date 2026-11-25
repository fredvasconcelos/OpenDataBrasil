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


/** O círculo do alerta acompanha o i, sem herdar a altura maior da área de toque. */
export async function expectCompactInfo(button: Locator) {
  const style = await button.evaluate(el => {
    const css = getComputedStyle(el);
    return { background: css.backgroundColor, shadow: css.boxShadow, border: css.borderTopWidth };
  });
  expect(style).toEqual({ background: "rgba(0, 0, 0, 0)", shadow: "none", border: "0px" });
  const geometry = await button.evaluate(el => {
    const symbol = el.querySelector(".info-symbol")!, svg = symbol.querySelector("svg")!;
    const circle = symbol.getBoundingClientRect(), icon = svg.getBoundingClientRect();
    const control = el.getBoundingClientRect();
    return { width: circle.width, height: circle.height, ratio: circle.width / icon.width,
      iconWidth: icon.width, controlWidth: control.width, controlHeight: control.height,
      dx: circle.x + circle.width / 2 - icon.x - icon.width / 2,
      dy: circle.y + circle.height / 2 - icon.y - icon.height / 2,
      radius: getComputedStyle(symbol).borderRadius,
      background: getComputedStyle(symbol).backgroundColor };
  });
  expect(geometry.width).toBeGreaterThanOrEqual(24);
  expect(geometry.iconWidth).toBeGreaterThanOrEqual(18);
  expect(geometry.width).toBeLessThanOrEqual(geometry.controlWidth);
  expect(geometry.height).toBeLessThanOrEqual(geometry.controlHeight);
  expect(Math.abs(geometry.width - geometry.height)).toBeLessThan(0.5);
  expect(geometry.ratio).toBeGreaterThan(1);
  expect(geometry.ratio).toBeLessThanOrEqual(1.5);
  expect(Math.abs(geometry.dx)).toBeLessThan(0.5);
  expect(Math.abs(geometry.dy)).toBeLessThan(0.5);
  expect(geometry.radius).toBe("50%");
  expect(geometry.background).not.toBe("rgba(0, 0, 0, 0)");
}
