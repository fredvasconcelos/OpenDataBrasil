import { expect, test } from "@playwright/test";
import { createRequire } from "node:module";

const loadModule = createRequire(`${process.cwd()}/package.json`);
const money = (value: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value).replace(/\u00a0/g, " ");

test("execução reconcilia seis fases, preserva negativos e cruza função com órgão", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const response = await request.get("/odb-api/contas/execucao?periods=2025&dimension=function");
  expect(response.ok()).toBeTruthy();
  const execution = await response.json();
  await page.goto("/contas/painel?lens=C&period=2025");
  await expect(page.locator(".contas-phase-cards li")).toHaveCount(6);
  for (const [phase, value] of Object.entries(execution.total)) {
    if (typeof value === "number") await expect(page.locator(`[data-phase="${phase}"] .contas-kpi-note`)).toHaveText(money(value));
  }
  await expect(page.getByRole("combobox", { name: "Sede cadastral do favorecido", exact: true })).toHaveCount(0);
  await expect(page.locator(".map-wrap")).toHaveCount(0);
  await page.getByRole("button", { name: execution.rows[0].label, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`filter=function%3A${execution.rows[0].category_code}`));
  await page.getByRole("combobox", { name: "Detalhar por", exact: true }).selectOption("organ");
  const crossed = await request.get(`/odb-api/contas/execucao?periods=2025&dimension=organ&filter=function%3A${execution.rows[0].category_code}`);
  const result = await crossed.json();
  await expect(page.locator('[data-phase="paid"] .contas-kpi-note')).toHaveText(money(result.total.paid));
  await page.reload();
  await expect(page.locator('[data-phase="paid"] .contas-kpi-note')).toHaveText(money(result.total.paid));
  await expect(page.locator(".contas-active-filters button")).toHaveCount(1);
  await page.locator(".contas-active-filters button").click();
  await expect(page).not.toHaveURL(/filter=/);
  expect(errors).toEqual([]);
});

test("pagamentos por UF e município reconciliam com a API e a ficha volta à lente B", async ({ page, request }) => {
  await page.goto("/contas/painel?lens=B&period=2025&geography=uf%3A25");
  const response = await request.get("/odb-api/contas/table?lens=B&geography_key=uf%3A25&periods=2025&group_by=recipient");
  expect(response.ok()).toBeTruthy();
  const result = await response.json();
  await expect(page.locator(".contas-federal > .contas-kpi .contas-kpi-value")).toHaveText(money(result.value_total));
  await expect(page.getByRole("combobox", { name: "Município da sede", exact: true }).locator("option")).toHaveCount(224);
  await page.getByRole("combobox", { name: "Município da sede", exact: true }).selectOption("municipio:2507507");
  const municipal = await request.get("/odb-api/contas/table?lens=B&geography_key=municipio%3A2507507&periods=2025&group_by=recipient");
  const local = await municipal.json();
  await expect(page.locator(".contas-federal > .contas-kpi .contas-kpi-value")).toHaveText(money(local.value_total));
  await expect(page.locator(".map-focus path.territory")).toHaveCount(223);
  await page.locator(".contas-federal .data-table tbody a").first().click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("link", { name: /Voltar ao painel/ }).click();
  await expect(page).toHaveURL(/lens=B/);
  await expect(page).toHaveURL(/geography=municipio%3A2507507/);
  await expect(page.locator(".contas-federal > .contas-kpi .contas-kpi-value")).toHaveText(money(local.value_total));
});

test("busca de PJ abre ficha e troca de lente limpa os recortes incompatíveis", async ({ page }) => {
  await page.goto("/contas/painel?lens=B&period=2026M01&geography=uf%3A25");
  await page.getByRole("searchbox", { name: "Buscar favorecido pessoa jurídica", exact: true }).fill("RAFAEL INDUSTRIA");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page.getByRole("link", { name: "RAFAEL INDUSTRIA E CONFECCOES LTDA", exact: true }).last()).toBeVisible();
  await page.getByRole("link", { name: "RAFAEL INDUSTRIA E CONFECCOES LTDA", exact: true }).last().click();
  await expect(page.getByRole("heading", { level: 1, name: "RAFAEL INDUSTRIA E CONFECCOES LTDA", exact: true })).toBeVisible();
  await page.getByRole("link", { name: /Voltar ao painel/ }).click();
  await page.getByRole("navigation", { name: "Perspectiva dos dados", exact: true }).getByRole("link", { name: "Execução orçamentária federal", exact: true }).click();
  await expect(page).toHaveURL(/\/contas\/painel\?lens=C$/);
  await expect(page.locator(".contas-phase-cards li")).toHaveCount(6);
});

test("falha da execução permite tentar novamente sem mostrar zero", async ({ page }) => {
  let unavailable = true;
  await page.route("**/odb-api/contas/execucao?**", (route) => unavailable ? route.fulfill({ status: 503, body: "{}", contentType: "application/json" }) : route.continue());
  await page.goto("/contas/painel?lens=C&period=2025");
  await expect(page.getByRole("heading", { name: "Contas públicas temporariamente indisponíveis", exact: true })).toBeVisible();
  await expect(page.locator(".contas-phase-cards")).toHaveCount(0);
  unavailable = false;
  await page.getByRole("button", { name: "Tentar de novo", exact: true }).click();
  await expect(page.locator(".contas-phase-cards li")).toHaveCount(6);
});

for (const lens of ["B", "C"]) {
  for (const width of [390, 1440]) {
    for (const theme of ["light", "dark"]) {
      test(`lente ${lens}: teclado, acessibilidade e largura ${width}, tema ${theme}`, async ({ page }) => {
        await page.setViewportSize({ width, height: 900 });
        await page.addInitScript((value) => localStorage.setItem("odbr-theme", value), theme);
        await page.goto(`/contas/painel?lens=${lens}&period=2025&geography=uf%3A25`);
        await expect(page.locator(".contas-federal .data-table tbody tr").first()).toBeVisible();
        if (theme === "dark") await page.locator("html").evaluate((html) => html.setAttribute("data-theme", "dark"));
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
        await page.addScriptTag({ path: loadModule.resolve("axe-core/axe.min.js") });
        const violations = await page.evaluate(async () => {
          const axe = (window as Window & { axe: { run: (root: Document, options: object) => Promise<{ violations: { id: string; nodes: { target: string[] }[] }[] }> } }).axe;
          return (await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } })).violations;
        });
        expect(violations).toEqual([]);
        await page.getByRole("combobox", { name: "Detalhar por", exact: true }).focus();
        await expect(page.getByRole("combobox", { name: "Detalhar por", exact: true })).toBeFocused();
        await page.screenshot({ path: test.info().outputPath(`lente-${lens}-${width}-${theme}.png`), fullPage: true });
      });
    }
  }
}

test("catálogo oferece as lentes finais e mantém os cartões da lente A", async ({ page }) => {
  await page.goto("/");
  await page.locator(".block-card[data-block=contas] button").click();
  await expect(page.getByRole("link", { name: "Pagamentos a favorecidos", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Empenhado", exact: true })).toHaveAttribute("href", "/contas/painel?lens=C#fase-committed");
  await expect(page.getByRole("link", { name: "Total enviado pela União", exact: true })).toBeVisible();
});


test("execução em página distante mantém totais e permite retornar a uma página válida", async ({ page, request }) => {
  const first = await (await request.get("/odb-api/contas/execucao?periods=2025&dimension=function")).json();
  await page.goto("/contas/painel?lens=C&period=2025&page=100");
  await expect(page.locator('[data-phase="paid"] .contas-kpi-note')).toHaveText(money(first.total.paid));
  await expect(page.getByText("Esta página não tem registros.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Página anterior", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`page=${first.pages}`));
  await expect(page.locator(".contas-execution-table tbody tr").first()).toBeVisible();
});
