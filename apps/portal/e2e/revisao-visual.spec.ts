import { expect, test } from "@playwright/test";

for (const theme of ["light", "dark"]) {
  test(`revisão visual: páginas, margens e aviso no tema ${theme}`, async ({ page }) => {
    test.setTimeout(180_000);
    await page.addInitScript(value => localStorage.setItem("odbr-theme", value), theme);
    for (const width of [1920, 1366, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: width === 1366 ? 768 : 1080 });
      for (const path of ["/", "/sobre", "/apoie", "/metricas", "/dashboard?kpi=populacao_residente&nivel=uf"]) {
        await page.goto(path);
        await expect(page.locator(".notice")).toBeVisible();
        const dimensions = await page.locator(".notice").evaluate(element => ({
          height: element.clientHeight, contentHeight: element.scrollHeight,
        }));
        expect(dimensions.contentHeight).toBeLessThanOrEqual(dimensions.height);
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
        await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
        if (width === 1920 || width === 390) {
          await page.screenshot({ path: `test-results/revisao-${theme}-${width}-${path.split("?")[0].replaceAll("/", "") || "inicio"}.png`, fullPage: true });
        }
      }
    }
  });
}

test("recuperação pontual: API ocupada mantém painel e oferece tentativa manual", async ({ page }) => {
  await page.route("**/odb-api/kpis/*/map*", route => route.fulfill({
    status: 503, json: { error: { code: "service_unavailable", message: "ocupado" } },
  }));
  await page.goto("/dashboard?kpi=populacao_residente&nivel=uf");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "O serviço está ocupado" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Tentar de novo", exact: true }).first()).toBeVisible();
});

// Escala de pixels + viewport equivalente: emula o espaço útil de zoom do navegador.
// Não substitui a conferência do mantenedor com a escala real de seu monitor.
test("revisão visual: escalas de 125%, 150% e 200% preservam páginas e exportação", async ({ browser }) => {
  test.setTimeout(120_000);
  for (const factor of [1.25, 1.5, 2]) {
    const context = await browser.newContext({
      viewport: { width: Math.floor(1920 / factor), height: Math.floor(1080 / factor) },
      deviceScaleFactor: factor, locale: "pt-BR",
    });
    const page = await context.newPage();
    for (const path of ["/", "/sobre", "/apoie", "/metricas", "/dashboard?kpi=populacao_residente&nivel=uf"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(Math.floor(1920 / factor));
    }
    // DS 2.18: abaixo de 992 px (1920 com escala de 200%) o Painel usa o layout móvel,
    // em que a exportação fica na aba Tabela.
    const views = page.getByRole("group", { name: "Visualização" });
    if (await views.isVisible()) await views.getByRole("button", { name: "Tabela" }).click();
    await page.getByRole("button", { name: "Exportar dados…", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Exportar dados", exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Baixar", exact: true })).toBeVisible();
    await page.screenshot({ path: `test-results/revisao-escala-${factor}.png`, fullPage: true });
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await context.close();
  }
});
