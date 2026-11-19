import { expect, test } from "@playwright/test";

import { openCatalog } from "./helpers";

test("índice leve: primeiro indicador, URL inválida e troca sem renderização do servidor", async ({ page, request }) => {
  const response = await request.get("/odb-api/portal/index");
  expect(response.ok()).toBeTruthy();
  const index = await response.json();
  const first = index.themes.flatMap((t: { subthemes: { kpis: { label: string }[] }[] }) => t.subthemes.flatMap((s) => s.kpis))[0];
  await page.goto("/dashboard?kpi=nao_existe");
  await expect(page.getByRole("heading", { level: 1, name: first.label, exact: true })).toBeVisible();
  const html = await request.get("/dashboard?kpi=populacao_estimada", { headers: { "Accept-Encoding": "identity" } });
  expect((await html.body()).length).toBeLessThan(300_000);

  let renders = 0;
  const metadata: string[] = [];
  page.on("request", (req) => {
    if (new URL(req.url()).pathname === "/dashboard" && new URL(req.url()).searchParams.has("kpi") && req.url().includes("_rsc=")) renders += 1;
    if (/\/odb-api\/kpis\/[^/?]+$/.test(req.url())) metadata.push(req.url());
  });
  const catalog = await openCatalog(page);
  await catalog.getByRole("searchbox").fill("população residente");
  const item = catalog.getByRole("button", { name: /População residente \(Censo\)/ });
  await item.focus();
  await expect.poll(() => metadata.length).toBe(1);
  await item.click();
  await expect(page.getByRole("heading", { level: 1, name: "População residente (Censo)", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Nível territorial", exact: true }).selectOption("uf");
  await expect(page).toHaveURL(/nivel=uf/);
  expect(renders).toBe(0);
  expect(metadata).toHaveLength(1);
});

test("recorte por UF, detalhes em lote e exportação com os períodos escolhidos", async ({ page }) => {
  let individualRequests = 0;
  page.on("request", (req) => { if (/\/detail\?/.test(req.url())) individualRequests += 1; });
  await page.goto("/dashboard?kpi=populacao_residente&nivel=uf&periodo=2022&dim=c2");
  const map = page.getByRole("img", { name: /População residente \(Censo\)/ });
  await expect(map.locator(".map-focus path.territory")).toHaveCount(27);
  const bahia = map.getByRole("button", { name: /^Bahia:/ });
  await bahia.hover();
  await expect(page.getByRole("tooltip")).toContainText("Mulheres");
  await map.getByRole("button", { name: /^São Paulo:/ }).hover();
  await expect(page.getByRole("tooltip")).toContainText("São Paulo");
  expect(individualRequests).toBe(0);
  await bahia.click();
  await page.getByRole("button", { name: "Ver municípios de Bahia", exact: true }).click();
  await expect(page).toHaveURL(/foco=uf%3A29/);
  await expect(map.locator(".map-focus path.territory")).toHaveCount(417);
  await expect(page.getByRole("navigation", { name: "Recorte do mapa" })).toContainText("Bahia");
  await page.screenshot({ path: "test-results/plano-d-desktop.png", fullPage: true });

  await page.getByRole("button", { name: "Exportar dados…", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Exportar dados", exact: true });
  await expect(dialog.getByRole("combobox", { name: "Estado (UF)", exact: true })).toHaveValue("uf:29");
  await dialog.getByRole("radio", { name: "JSON", exact: true }).check();
  const pending = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Baixar", exact: true }).click();
  const file = await pending;
  const body = JSON.parse(await (await file.createReadStream())!.toArray().then((parts) => Buffer.concat(parts).toString()));
  expect(body.rows.length).toBeGreaterThan(0);
  expect(new Set(body.rows.map((row: { periodo: string }) => row.periodo))).toEqual(new Set(["2022"]));
  expect(body.metadata.filtros.within).toBe("uf:29");
  expect(body.metadata.filtros.periods_by_grain).toEqual({ ano: ["2022"] });
  expect(individualRequests).toBe(0);
});

test("recorte municipal por teclado e janela de exportação no celular", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await page.goto("/dashboard?kpi=populacao_residente&nivel=uf&periodo=2022");
  await page.getByRole("button", { name: /^Filtros/ }).click();
  await page.getByRole("combobox", { name: "Municípios de", exact: true }).selectOption("uf:35");
  await page.getByRole("button", { name: "Ver resultado", exact: true }).click();
  await expect(page).toHaveURL(/foco=uf%3A35/);
  await expect(page.locator(".map-focus path.territory")).toHaveCount(645);
  await expect(page.locator(".map-loading")).toHaveCount(0);
  await page.screenshot({ path: "test-results/plano-d-celular.png", fullPage: true });
  await page.getByRole("button", { name: "Tabela", exact: true }).click();
  await page.getByRole("button", { name: "Exportar dados…", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Exportar dados", exact: true });
  await expect(dialog.getByRole("combobox", { name: "Estado (UF)", exact: true })).toHaveValue("uf:35");
  await expect(dialog.getByRole("button", { name: "Baixar", exact: true })).toBeEnabled();
  await dialog.getByRole("button", { name: "Baixar", exact: true }).scrollIntoViewIfNeeded();
  await expect(dialog.getByRole("button", { name: "Baixar", exact: true })).toBeInViewport();
  await page.screenshot({ path: "test-results/plano-d-exportacao-celular.png", fullPage: false });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await context.close();
});

test("IPCA mantém recorte municipal sem inventar valores de UF", async ({ page }) => {
  const invalid: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400 && response.url().includes("/odb-api/")) invalid.push(response.url());
  });
  await page.goto("/dashboard?kpi=ipca&nivel=municipio&foco=uf:35");
  await expect(page.getByRole("navigation", { name: "Recorte do mapa" })).toContainText("São Paulo");
  await expect(page.getByRole("combobox", { name: "Municípios de", exact: true })).toHaveValue("uf:35");
  await expect(page.locator(".map-focus path.territory")).toHaveCount(645);
  await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
  expect(invalid).toEqual([]);
});
