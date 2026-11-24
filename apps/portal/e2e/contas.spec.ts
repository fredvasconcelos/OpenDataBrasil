import { expect, test } from "@playwright/test";
import { createRequire } from "node:module";

const loadModule = createRequire(`${process.cwd()}/package.json`);

test("endereços antigos preservam os filtros e parâmetros repetidos", async ({ request }) => {
  const response = await request.get("/dashboard?kpi=populacao_residente&dim=c2&dim=c86&periodo=2022", { maxRedirects: 0 });
  expect(response.status()).toBe(308);
  const destination = new URL(response.headers().location!, "http://portal");
  expect(destination.pathname).toBe("/estatisticas/painel");
  expect(destination.searchParams.getAll("dim")).toEqual(["c2", "c86"]);
  expect(destination.searchParams.get("periodo")).toBe("2022");
});

test("dois blocos no Início e seletor acessível pelo teclado", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "O que você quer consultar?", exact: true })).toBeVisible();
  const button = page.getByRole("button", { name: "Painel de análise", exact: true });
  await button.click();
  const dialog = page.getByRole("dialog", { name: "Escolha o painel", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("link").first()).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(button).toBeFocused();
  await page.screenshot({ path: "test-results/cp5-inicio.png", fullPage: true });
});

test("503 das contas permite tentar novamente e mantém Estatísticas acessíveis", async ({ page }) => {
  let unavailable = true;
  await page.route("**/odb-api/contas/meta", (route) => unavailable
    ? route.fulfill({ status: 503, contentType: "application/json", body: '{"error":{"code":"unavailable"}}' })
    : route.continue());
  await page.goto("/contas/painel");
  await expect(page.getByRole("heading", { name: "Contas públicas temporariamente indisponíveis", exact: true })).toBeVisible();
  unavailable = false;
  await page.getByRole("button", { name: "Tentar de novo", exact: true }).click();
  await expect(page.locator(".contas-highlights")).toBeVisible({ timeout: 30_000 });
  await page.goto("/estatisticas/painel?kpi=populacao_residente&nivel=uf");
  await expect(page.getByRole("heading", { level: 1, name: "População residente (Censo)", exact: true })).toBeVisible();
});

test("contas reais: filtros na URL, valores da API, ranking e ficha sem identificadores", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/contas/painel?geography=uf%3A25&period=2025");
  await expect(page.locator(".contas-highlights")).toContainText("R$ 25.651.839.651,83", { timeout: 30_000 });
  await expect(page.locator(".map-focus path.territory")).toHaveCount(223);
  await expect(page.locator(".map-context path.territory")).toHaveCount(26);
  await page.getByRole("combobox", { name: "Área", exact: true }).selectOption("10");
  await expect(page).toHaveURL(/area=10/);
  await expect(page.locator(".contas-highlights")).toBeVisible();
  await expect(page.getByText("Área selecionada: Saúde", { exact: true })).toBeVisible();
  await expect(page.locator(".contas-who")).toContainText("Ranking de 2025, em todas as áreas e meses do ano.");
  await page.getByRole("button", { name: "Próxima página", exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.locator(".contas-ranking-foot")).toContainText("Página 2 de");
  const name = await page.locator(".contas-table tbody a").first().innerText();
  await page.locator(".contas-table tbody a").first().click();
  await expect(page.getByRole("heading", { name, level: 1, exact: true })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  const response = await request.get(page.url());
  expect(response.headers()["x-robots-tag"]).toContain("noindex");
  expect(await page.locator(".recipient-page").innerText()).not.toMatch(/\d{2}\.\d{3}\.\d{3}\/\d{4}|\*{3}\.\d{3}\.\d{3}/);
  expect(errors).toEqual([]);
  await page.screenshot({ path: "test-results/cp5-ficha.png", fullPage: true });
  await page.getByRole("link", { name: "Voltar ao painel", exact: true }).click();
  await expect(page.locator(".contas-ranking-foot")).toContainText("Página 2 de");
  await expect(page.getByRole("combobox", { name: "Área", exact: true })).toHaveValue("10");
  expect(new URL(page.url()).searchParams.get("period")).toBe("2025");
});

test("município e mês incompleto preservam o recorte e as notas oficiais", async ({ page }) => {
  await page.goto("/contas/painel?geography=uf%3A25&period=2025");
  await expect(page.locator(".contas-highlights")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("combobox", { name: "Território", exact: true }).selectOption("municipio:2507507");
  await expect(page.getByRole("heading", { level: 1, name: "João Pessoa · 2025", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Período", exact: true }).selectOption("2026M10");
  await expect(page).toHaveURL(/period=2026M10/);
  await expect(page.locator(".period-alerts")).toContainText("Mês incompleto");
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "João Pessoa · out/2026", exact: true })).toBeVisible();
});

for (const width of [1920, 390]) {
  test(`contas em claro e escuro, largura ${width}, sem rolagem lateral`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/contas/painel?geography=uf%3A25&period=2025");
    await expect(page.locator(".contas-highlights")).toBeVisible({ timeout: 30_000 });
    const compositionFits = await page.locator(".contas-how-card").evaluate((el) => el.scrollHeight <= el.clientHeight + 1);
    expect(compositionFits).toBe(true);
    for (const theme of ["light", "dark"]) {
      await page.evaluate((theme) => { document.documentElement.dataset.theme = theme; }, theme);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.screenshot({ path: `test-results/cp5-${width}-${theme}.png`, fullPage: true, animations: "disabled" });
    }
    if (width < 992) {
      await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
      const drawer = page.getByRole("dialog", { name: "Menu", exact: true });
      await expect(drawer.getByRole("link", { name: /Estatísticas oficiais/ })).toBeVisible();
      await expect(drawer.getByRole("link", { name: /Contas públicas/ })).toHaveAttribute("aria-current", "page");
    }
  });
}

test("acessibilidade automática das contas, nos dois temas", async ({ page }) => {
  // Mede as cores estáveis de cada tema, sem capturar a transição entre claro e escuro.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/contas/painel?geography=uf%3A25&period=2025");
  await expect(page.locator(".contas-highlights")).toBeVisible({ timeout: 30_000 });
  await page.addScriptTag({ path: loadModule.resolve("axe-core/axe.min.js") });
  for (const theme of ["light", "dark"]) {
    await page.evaluate((theme) => { document.documentElement.dataset.theme = theme; }, theme);
    const violations = await page.evaluate(async () => {
      const axe = (window as Window & { axe: { run: (root: Document, options: object) => Promise<{ violations: { id: string; nodes: { target: string[] }[] }[] }> } }).axe;
      const result = await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } });
      return result.violations.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target) }));
    });
    expect(violations, theme).toEqual([]);
  }
});
