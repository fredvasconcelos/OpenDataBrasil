import { expect, test } from "@playwright/test";

const panel = "/dashboard?kpi=despesa_familiar&nivel=uf&foco=regiao%3A2&periodo=2018";

test("consumo usa subtotal oficial e preserva a despesa familiar total", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`${panel}&dim=c12190`);
  const row = page.locator('.pivot-table tbody tr[data-key="uf:25"]');
  await expect(row).toContainText("2.893,59");
  await expect(row).toContainText("Base do grupo: 2.349,91");
  await expect(row).toContainText("21,1%");
  await expect(page.getByRole("combobox", { name: "Calcular % por", exact: true })).toBeVisible();
  await page.getByRole("button", { name: /^Paraíba:/ }).hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toContainText("2.349,91 (100,0%)");
  await expect(tooltip).toContainText("21,1%");
  await expect(tooltip).toHaveCSS("opacity", "1");
  await page.screenshot({ path: "test-results/percentuais-consumo-desktop.png" });
  await page.mouse.move(1900, 10);
  await page.getByRole("button", { name: /^Paraíba:/ }).click();
  const chart = page.getByRole("img", { name: /^Evolução temporal: Paraíba/ });
  await chart.focus();
  await chart.press("End");
  const seriesTip = page.locator(".series-tip");
  await expect(seriesTip).toContainText("496,1 (21,1%)");
  await expect(seriesTip).toContainText("Base do grupo: 2.349,91 (100,0%)");
  const tipBounds = await seriesTip.boundingBox();
  const plotBounds = await page.locator(".series-plot").boundingBox();
  expect(tipBounds!.y + tipBounds!.height).toBeLessThanOrEqual(plotBounds!.y + plotBounds!.height);
  await page.screenshot({ path: "test-results/percentuais-serie-desktop.png" });
});

test("renda explicita composição do portal e não substitui o Total oficial", async ({ page }) => {
  await page.goto(`${panel}&dim=c339`);
  const row = page.locator('.pivot-table tbody tr[data-key="uf:25"]');
  await expect(row).toContainText("Base exibida: 56.282,82");
  await expect(row).toContainText("2.893,59");
  await expect(page.locator(".table-box")).toContainText("não é participação oficial ponderada");
  await page.getByRole("button", { name: /^Paraíba:/ }).hover();
  await expect(page.getByRole("tooltip")).toContainText("Composição calculada pelo portal");
  await expect(page.getByRole("tooltip")).toHaveCSS("opacity", "1");
  await page.screenshot({ path: "test-results/percentuais-renda-desktop.png" });
});

test("dois níveis mostram percentuais na matriz e mantêm a hierarquia ao trocar eixos", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`${panel}&dim=c339,c12190`);
  const rows = page.locator('.pivot-table tbody tr[data-key="uf:25"]');
  await expect(rows).toContainText("2,3%");
  await page.getByRole("button", { name: /^Paraíba:/ }).hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip.locator(".tt-grid-share")).toHaveCount(77);
  await expect(tooltip.locator(".tt-summary .tt-share")).toHaveCount(7);
  await expect(tooltip).toHaveCSS("opacity", "1");
  const bounds = await tooltip.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(1080);
  await page.screenshot({ path: "test-results/percentuais-matriz-desktop.png" });
  await page.mouse.move(1900, 10);
  const before = await page.locator(".pivot-table .share").allTextContents();
  await page.getByRole("button", { name: "Trocar linhas e colunas", exact: true }).click();
  await expect(page.locator(".pivot-table tbody tr")).toHaveCount(96);
  await expect.poll(async () => (await page.locator(".pivot-table .share").allTextContents()).sort())
    .toEqual(before.sort());
  await page.screenshot({ path: "test-results/percentuais-eixos-desktop.png" });
});

test("percentuais e base permanecem acessíveis no celular", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${panel}&dim=c12190`);
  await page.getByRole("group", { name: "Visualização" }).getByRole("button", { name: "Tabela", exact: true }).click();
  const row = page.locator('.pivot-table tbody tr[data-key="uf:25"]');
  await expect(row).toContainText("21,1%");
  await page.locator(".share-base select").selectOption("none");
  await expect(row.locator(".share")).toHaveCount(0);
  await page.locator(".share-base select").selectOption("total");
  await expect(row).toContainText("21,1%");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
  await page.locator(".area-table").scrollIntoViewIfNeeded();
  await row.locator("td").nth(1).scrollIntoViewIfNeeded();
  await row.evaluate((el) => {
    const wrap = el.closest<HTMLElement>(".table-wrap")!;
    const food = el.querySelectorAll("td")[1]!;
    const territory = el.querySelector("th")!;
    wrap.scrollLeft += food.getBoundingClientRect().left - territory.getBoundingClientRect().right - 8;
    el.scrollIntoView({ block: "center", inline: "nearest" });
  });
  await page.screenshot({ path: "test-results/percentuais-consumo-celular.png" });
});
