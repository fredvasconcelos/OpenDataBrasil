import { expect, test } from "@playwright/test";

// Página Métricas (DS 2.12, ADR-0027). Enquanto a coleta não existe, a API de métricas
// responde 404 e a página diz que a coleta não começou: nenhum número aparece.
test("Métricas: item no menu entre Contato e Apoie, período e estado sem coleta", async ({ page }) => {
  await page.goto("/metricas");
  const nav = page.getByRole("navigation", { name: "Principal" });
  const metrics = nav.getByRole("link", { name: "Métricas" });
  await expect(metrics).toHaveAttribute("aria-current", "page");
  // Métricas é o último item do menu; o Apoie vem logo depois, fora dele.
  await expect(nav.getByRole("link").last()).toHaveText("Métricas");
  await expect(page.getByRole("heading", { level: 1, name: "Métricas do portal" })).toBeVisible();
  const period = page.getByRole("group", { name: "Período" });
  await expect(period.getByRole("button", { name: "30 dias" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { name: "A coleta de acessos ainda não começou" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Como contamos" })).toBeVisible();
  // Nada de números sem coleta: nem o total, nem o ranking.
  await expect(page.getByRole("heading", { name: "Número de acessos ao portal" })).toHaveCount(0);
  // Personalizado: valida antes de pedir à API.
  await period.getByRole("button", { name: "Personalizado" }).click();
  await page.getByLabel("De", { exact: true }).fill("2026-11-16");
  await page.getByLabel("Até", { exact: true }).fill("2026-11-01");
  await page.getByRole("button", { name: "Aplicar" }).click();
  await expect(page.locator(".metrics-error[role=alert]")).toHaveText("A data inicial vem depois da final.");
  await page.screenshot({ path: "test-results/metricas-sem-coleta.png", fullPage: true });
});
