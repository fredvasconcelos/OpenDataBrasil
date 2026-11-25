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


/** O alerta colore o i; o botão mantém a área de toque sem desenhar um selo ao redor. */
export async function expectPlainInfo(button: Locator) {
  const style = await button.evaluate(el => {
    const css = getComputedStyle(el);
    return { background: css.backgroundColor, shadow: css.boxShadow, border: css.borderTopWidth };
  });
  expect(style).toEqual({ background: "rgba(0, 0, 0, 0)", shadow: "none", border: "0px" });
}
