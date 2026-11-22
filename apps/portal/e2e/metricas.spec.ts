import { expect, test } from "@playwright/test";

// Página Métricas (DS 2.12, ADR-0027). Enquanto a coleta não existe, a API de métricas
// responde 404 e a página diz que a coleta não começou: nenhum número aparece.
test("Métricas: item no menu entre Contato e Apoie, período e estado sem coleta", async ({ page }) => {
  // Simula a ausência de coleta sem depender do banco ou da versão da API local.
  await page.route("**/odb-api/metrics/**", route => route.fulfill({
    status: 404, json: { error: { code: "not_found", message: "A coleta de acessos ainda não começou" } },
  }));
  await page.goto("/metricas");
  const nav = page.getByRole("navigation", { name: "Principal" });
  const metrics = nav.getByRole("link", { name: "Métricas" });
  await expect(metrics).toHaveAttribute("aria-current", "page");
  // Métricas é o último item do menu; o Apoie vem logo depois, fora dele.
  await expect(nav.getByRole("link").last()).toHaveText("Métricas");
  await expect(page.getByRole("heading", { level: 1, name: "Métricas do portal" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Período" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "A coleta de acessos ainda não começou" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Como contamos" })).toHaveCount(0);
  // Nada de números sem coleta: nem o total, nem o ranking.
  await expect(page.getByRole("heading", { name: "Número de acessos ao portal" })).toHaveCount(0);
  await page.screenshot({ path: "test-results/metricas-sem-coleta.png", fullPage: true });
});
