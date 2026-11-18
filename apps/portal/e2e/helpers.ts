import type { Page } from "@playwright/test";

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
