import { expect, test } from "@playwright/test";

for (const theme of ["light", "dark"]) {
  test(`acumulado entre anos com subtotal e teclado no tema ${theme}`, async ({ page }) => {
    await page.addInitScript(value => localStorage.setItem("odbr-theme", value), theme);
    await page.goto("/estatisticas/painel?kpi=sinesp_homicidio_doloso&nivel=uf&grao=trimestre&isolar=1&acumular=1&periodo=2023,2026&territorio=uf:25");
    await expect(page.locator(".season-bar")).toHaveCount(4);
    const warning = page.getByRole("button", { name: "Sobre o método do gráfico: dados parciais", exact: true });
    await expect(warning).toHaveAttribute("aria-expanded", "false");
    await warning.focus();
    await page.keyboard.press("Enter");
    await expect(warning).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".seasonal-alerts")).toContainText("out 2026");
    await expect(page.locator(".chart-info")).toContainText("2023 e 2026");
    await page.getByText("Valores e cobertura das barras", { exact: true }).click();
    await expect(page.locator(".seasonal-result")).toContainText("períodos com valor");
    await page.screenshot({ path: `test-results/sazonal-${theme}.png`, fullPage: true });
  });
}

test("trimestral de grão único permite Isolar sem habilitar soma", async ({ page }) => {
  await page.goto("/estatisticas/painel?kpi=forca_trabalho_v1641&nivel=brasil&isolar=1&periodo=2024,2025");
  await expect(page.getByRole("checkbox", { name: "Isolar período", exact: true })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Acumular", exact: true })).toBeDisabled();
  await expect(page.locator(".season-bar")).toHaveCount(8);
  await expect(page.locator(".season-figure .series-legend")).toContainText("2024");
  await expect(page.locator(".failure")).toHaveCount(0);
});

test("anual compara os anos e mantém população sem soma", async ({ page }) => {
  await page.goto("/estatisticas/painel?kpi=populacao_estimada&nivel=brasil&isolar=1&periodo=2024,2025");
  await expect(page.getByRole("checkbox", { name: "Acumular", exact: true })).toBeDisabled();
  await expect(page.locator(".season-bar")).toHaveCount(2);
  await expect(page.locator(".season-figure")).toContainText("2025");
});

test("anual soma o intervalo por categoria sem acrescentar o Total às folhas", async ({ page }) => {
  const response = page.waitForResponse(r => r.url().includes("/seasonal") && r.status() === 200);
  await page.goto("/estatisticas/painel?kpi=casamentos&nivel=uf&dim=c664&isolar=1&acumular=1&periodo=2023,2024&territorio=uf:25");
  const data = await (await response).json();
  const leaves = data.series.filter((s: { depth: number }) => s.depth === 1);
  expect(leaves).toHaveLength(4);
  await expect(page.locator(".season-bar")).toHaveCount(4);
  await expect(page.locator(".season-figure .series-legend")).not.toContainText("Total");
  await page.getByRole("checkbox", { name: "Acumular", exact: true }).click();
  await expect(page.locator(".season-bar")).toHaveCount(8);
  await expect(page.locator(".season-figure .series-legend")).toContainText("2024");
});

test("acumulado sazonal é legível no celular", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/estatisticas/painel?kpi=sinesp_homicidio_doloso&nivel=uf&grao=trimestre&isolar=1&acumular=1&periodo=2023,2026&territorio=uf:25");
  await page.getByRole("button", { name: "Série", exact: true }).click();
  await expect(page.locator(".season-bar")).toHaveCount(4);
  await expect(page.getByRole("button", { name: "Sobre o método do gráfico: dados parciais", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/sazonal-mobile.png", fullPage: true });
});
