import { devices, expect, test, type Page } from "@playwright/test";

// Versão mobile (DS v2.5, plano B3): cabeçalho com gaveta, painel inferior de filtros e
// indicadores, abas Mapa/Série/Tabela e cartão do território tocado. Roda no Chromium com
// a emulação dos aparelhos (tela, toque e user agent); o WebKit não está no projeto.
const phones = {
  "iPhone 13": devices["iPhone 13"],
  "Pixel 7": devices["Pixel 7"],
};

const noHorizontalScroll = async (page: Page) =>
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    await page.evaluate(() => window.innerWidth),
  );

for (const [name, device] of Object.entries(phones)) {
  // defaultBrowserType não pode ser trocado dentro de um grupo; o resto da emulação sim.
  const { defaultBrowserType: _browser, ...emulation } = device;
  void _browser;

  test.describe(`mobile · ${name}`, () => {
    test.use(emulation);

    test("nenhuma página rola para o lado", async ({ page }) => {
      for (const path of ["/", "/sobre", "/apoie", "/metricas", "/dashboard?kpi=populacao_residente&nivel=uf"]) {
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        await noHorizontalScroll(page);
      }
    });

    test("gaveta de menu: abre, navega e fecha com Esc", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("navigation", { name: "Principal" })).toBeHidden();
      const menu = page.getByRole("button", { name: "Abrir menu" });
      await menu.tap();
      const drawer = page.getByRole("dialog", { name: "Menu" });
      await expect(drawer).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(drawer).toBeHidden();
      await expect(menu).toBeFocused();
      await menu.tap();
      await drawer.getByRole("link", { name: "Sobre os dados" }).tap();
      await expect(page).toHaveURL(/\/sobre$/);
      await expect(drawer).toBeHidden();
    });

    test("painel: abas, toque no mapa, aproximar e painéis inferiores", async ({ page }) => {
      await page.goto("/dashboard?kpi=populacao_residente&nivel=uf");
      const views = page.getByRole("group", { name: "Visualização" });
      await expect(views.getByRole("button", { name: "Mapa" })).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator(".area-table")).toBeHidden();

      // Toque num estado: cartão com nome e valor; "Aproximar" desce para os municípios.
      await page.locator("path.territory").first().waitFor();
      await page.locator("path.territory").nth(5).tap();
      const picked = page.locator(".area-picked");
      await expect(picked).toBeVisible();
      await expect(picked.locator("strong")).not.toBeEmpty();
      await picked.getByRole("button", { name: /^Ver municípios de / }).tap();
      await expect(page).toHaveURL(/nivel=municipio/);

      // Abas: a tabela aparece sozinha; o mapa some.
      await views.getByRole("button", { name: "Tabela" }).tap();
      await expect(page.locator(".area-table")).toBeVisible();
      await expect(page.locator(".area-map")).toBeHidden();

      // Filtros num painel inferior modal; Esc fecha.
      const bar = page.getByRole("group", { name: "Ações do painel" });
      await bar.getByRole("button", { name: /Filtros/ }).tap();
      const sheet = page.getByRole("dialog", { name: "Filtros" });
      await expect(sheet).toBeVisible();
      await expect(sheet.getByLabel("Nível territorial")).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(sheet).toBeHidden();

      // Indicadores: escolher outro KPI fecha o painel e troca o indicador.
      await bar.getByRole("button", { name: "Indicadores" }).tap();
      const themes = page.getByRole("dialog", { name: "Temas e indicadores" });
      await expect(themes).toBeVisible();
      await themes.getByRole("button", { name: "Área territorial" }).first().tap();
      await expect(themes).toBeHidden();
      await expect(page).toHaveURL(/kpi=area_territorial/);
      await noHorizontalScroll(page);
    });
  });
}

test("desktop não mostra a barra inferior, as abas nem o botão de menu", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_residente&nivel=uf");
  await expect(page.locator(".mobile-bar")).toBeHidden();
  await expect(page.locator(".area-views")).toBeHidden();
  await expect(page.getByRole("button", { name: "Abrir menu" })).toBeHidden();
  await expect(page.getByRole("navigation", { name: "Principal" })).toBeVisible();
});
