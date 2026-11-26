import { expect, test } from "@playwright/test";

test("Início revela somente os indicadores do bloco escolhido", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("searchbox")).toHaveCount(0);
  await page.screenshot({ path: "test-results/revisao-inicio.png", fullPage: true });
  await expect(page.locator(".theme-grid")).toHaveCount(0);
  await page.getByRole("button", { name: "Ver indicadores: Estatísticas oficiais", exact: true }).click();
  await expect(page.getByRole("searchbox", { name: "Buscar indicador", exact: true })).toBeVisible();
  await expect(page.locator(".theme-grid")).toBeVisible();
  await page.screenshot({ path: "test-results/revisao-inicio-estatisticas.png", fullPage: true });
  await page.getByRole("button", { name: "Ver indicadores: Contas públicas", exact: true }).click();
  await expect(page.locator(".theme-grid")).toHaveCount(0);
  await expect(page.getByRole("searchbox", { name: "Buscar indicador de contas públicas", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Consultar indicador", exact: true })).toHaveAttribute("href", "/contas/painel");
  await page.screenshot({ path: "test-results/revisao-inicio-contas.png", fullPage: true });
  for (const theme of ["light", "dark"]) {
    await page.evaluate((theme) => { document.documentElement.dataset.theme = theme; }, theme);
    const colors = await page.locator(".block-card").evaluateAll((cards) => cards.map((el) => getComputedStyle(el).borderTopColor));
    expect(colors[0]).toBe(colors[1]);
  }
  await page.getByRole("searchbox").fill("IPCA");
  await expect(page.getByRole("status")).toContainText("Nenhum indicador de contas públicas encontrado.");
});

test("área atualiza os cinco cartões e recebedores sem desmontar o mapa", async ({ page, request }) => {
  await page.goto("/contas/painel?geography=uf%3A25&period=2025");
  await expect(page.locator(".contas-highlights")).toContainText("R$ 25.651.839.651,83", { timeout: 30_000 });
  const expected = await (await request.get("/odb-api/contas/table?lens=A&geography_key=uf%3A25&periods=2025&group_by=transfer_type&filter=function%3A10")).json();
  const map = await page.locator(".contas-map-wrap svg").first().elementHandle();
  const cards = await page.locator(".contas-highlights").elementHandle();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/odb-api/contas/table?**", async (route) => {
    if (new URL(route.request().url()).searchParams.has("filter")) await gate;
    await route.continue();
  });
  await page.locator(".contas-area-scroll").getByRole("button", { name: /^Saúde/ }).click();
  await expect(page.locator(".contas-content")).toHaveAttribute("aria-busy", "true");
  expect(await map!.evaluate((el) => el.isConnected)).toBe(true);
  expect(await cards!.evaluate((el) => el.isConnected)).toBe(true);
  await expect(page.locator(".contas-highlights > li")).toHaveCount(5);
  await expect(page.locator(".contas-highlights")).toContainText("R$ 25.651.839.651,83");
  release();
  await expect(page.locator(".contas-content")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".contas-highlights .is-main")).toContainText(expected.value_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }).replace(/\u00a0/g, " "));
  await expect(page.locator(".contas-highlights")).toContainText("Sem registros neste recorte");
  await expect(page.locator(".contas-who")).toContainText("2025 · Saúde");
  await expect(page.locator(".contas-when .series-legend li")).toHaveCount(1);
  await expect(page.locator(".contas-when .series-legend")).toHaveText("Saúde");
  expect(await map!.evaluate((el) => el.isConnected)).toBe(true);
  const recipients = await (await request.get("/odb-api/contas/table?lens=A&geography_key=uf%3A25&periods=2025&group_by=recipient&filter=function%3A10")).json();
  await expect(page.locator(".contas-table tbody a").first()).toHaveText(recipients.rows[0].recipient.name);
  await page.screenshot({ path: "test-results/revisao-contas-saude.png", fullPage: true });
  await page.getByRole("button", { name: "Limpar todos os filtros", exact: true }).click();
  await expect(page).toHaveURL(/\/contas\/painel$/);
  await expect(page.getByRole("heading", { level: 1, name: "Brasil · 2025", exact: true })).toBeVisible();
});

test("Estatísticas oferece uma única limpeza junto aos filtros", async ({ page }) => {
  await page.goto("/estatisticas/painel?kpi=populacao_residente&nivel=uf&territorio=uf%3A25&dim=c2");
  const clear = page.getByRole("button", { name: "Limpar todos os filtros", exact: true });
  await expect(clear).toHaveCount(1);
  await expect(page.locator(".sidebar .filters")).toContainText("Limpar todos os filtros");
  await expect(clear).toBeEnabled();
  await clear.click();
  await expect(clear).toBeDisabled();
  const query = new URL(page.url()).searchParams;
  expect(query.get("kpi")).toBe("populacao_residente");
  expect(query.has("dim")).toBe(false);
  expect(query.has("territorio")).toBe(false);
});

for (const width of [3440, 2560, 1920, 1440, 390]) {
  test(`cinco blocos, mapa contido e áreas com rolagem, largura ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1080 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/contas/painel?period=2025");
    await expect(page.locator(".contas-highlights")).toBeVisible({ timeout: 30_000 });
    const areas = page.locator(".contas-area-scroll");
    const scroll = await areas.evaluate((el) => ({ scroll: el.scrollHeight, height: el.clientHeight, count: el.children.length }));
    expect(scroll.count).toBeGreaterThan(10);
    expect(scroll.scroll).toBeGreaterThan(scroll.height);
    const typeBefore = await page.locator("#como-tipo").boundingBox();
    await areas.evaluate((el) => el.scrollTo(0, el.scrollHeight));
    expect(await page.locator("#como-tipo").boundingBox()).toEqual(typeBefore);
    await areas.evaluate((el) => el.scrollTo(0, 0));
    const map = await page.locator(".contas-map-wrap .map-panel").boundingBox();
    for (const selector of [".map-hint", ".legend", ".map-zoom"]) {
      const box = await page.locator(`.contas-map-wrap ${selector}`).boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(map!.x);
      expect(box!.x + box!.width).toBeLessThanOrEqual(map!.x + map!.width + 1);
      expect(box!.y + box!.height).toBeLessThanOrEqual(map!.y + map!.height + 1);
    }
    const chart = await page.locator(".contas-when .series-plot").boundingBox();
    const card = await page.locator(".contas-when").boundingBox();
    expect(chart!.height).toBeGreaterThan(100);
    expect(chart!.y + chart!.height).toBeLessThanOrEqual(card!.y + card!.height);
    if (width >= 1600) {
      const highlights = await page.locator(".contas-highlights").boundingBox();
      const recipients = await page.locator(".contas-who").boundingBox();
      expect(Math.abs(highlights!.x + highlights!.width - recipients!.x - recipients!.width)).toBeLessThan(1);
      const textSize = await page.locator(".contas-table td").first().evaluate(el => parseFloat(getComputedStyle(el).fontSize));
      expect(textSize).toBeGreaterThanOrEqual(13);
      const when = await page.locator(".contas-when").boundingBox();
      const who = await page.locator(".contas-who").boundingBox();
      expect(when!.y).toBeGreaterThan(map!.y);
      expect(Math.max(when!.y + when!.height, who!.y + who!.height)).toBeLessThan(1080);
    }
    for (const theme of ["light", "dark"]) {
      await page.evaluate((theme) => { document.documentElement.dataset.theme = theme; }, theme);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.screenshot({ path: `test-results/revisao-contas-${width}-${theme}.png`, fullPage: true, animations: "disabled" });
    }
  });
}
