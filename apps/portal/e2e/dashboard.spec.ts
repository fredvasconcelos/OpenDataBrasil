import { expect, test } from "@playwright/test";

// Fluxo do critério de aceitação da Fase 5: pesquisar, abrir o indicador, filtrar
// território e período, ver gráfico e mapa, identificar a fonte e exportar.
test("pesquisa, painel, tooltip, seleção e exportação", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Buscar indicador").fill("populacao residente");
  await page.getByRole("link", { name: "População residente (Censo)" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "População residente (Censo)" })).toBeVisible();

  const map = page.getByRole("img", { name: /População residente \(Censo\)/ });
  await expect(map.locator("path.territory")).toHaveCount(27);

  // Dimensões: cor ou raça > sexo, e tooltip aninhado no território sob o ponteiro.
  // As caixas refletem a URL (atualizada de forma assíncrona): clicar e esperar.
  await page.getByLabel("Cor ou raça").click();
  await expect(page.getByLabel("Cor ou raça")).toBeChecked();
  await page.getByLabel("Sexo").click();
  await expect(page.getByLabel("Sexo")).toBeChecked();
  await expect(page).toHaveURL(/dim=c86%2Cc2|dim=c86,c2/);
  const bahia = map.getByRole("button", { name: /^Bahia:/ });
  await bahia.hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toContainText("Bahia");
  await expect(tooltip).toContainText("Parda");
  await expect(tooltip).toContainText("57,3%");
  await page.screenshot({ path: "test-results/painel-tooltip.png", fullPage: false });

  // Clique seleciona o território: a série mostra a Bahia em 2010 e 2022.
  await bahia.click();
  await expect(page).toHaveURL(/territorio=uf%3A29|territorio=uf:29/);
  await expect(page.getByRole("heading", { name: /Evolução temporal · Bahia/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /Evolução temporal: Bahia/ })).toBeVisible();

  // Período e nível.
  await page.getByLabel("Período").selectOption("2010");
  await expect(page.getByRole("heading", { name: /Dados · Estado \(UF\) · 2010/ })).toBeVisible();
  await page.getByLabel("Nível territorial").selectOption("regiao");
  await expect(map.locator("path.territory")).toHaveCount(5);

  // Fonte visível.
  await expect(page.getByText(/Tabela SIDRA 9606/)).toBeVisible();

  // Exportação CSV (ZIP com metadados).
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV" }).click();
  expect((await download).suggestedFilename()).toBe("populacao_residente_regiao.zip");
  await page.screenshot({ path: "test-results/painel-regioes.png", fullPage: true });
});

test("mapa municipal e KPI sem dimensões", async ({ page }) => {
  await page.goto("/dashboard?kpi=pessoas_quilombolas&nivel=municipio");
  const map = page.getByRole("img", { name: /Pessoas quilombolas/ });
  await expect(map.locator("path.territory")).toHaveCount(5570, { timeout: 30_000 });
  await page.getByLabel("Sexo").click();
  await expect(page.getByLabel("Sexo")).toBeChecked();
  await map.getByRole("button", { name: /^Alcântara:/ }).hover();
  await expect(page.getByRole("tooltip")).toContainText("Homens");
  await page.screenshot({ path: "test-results/painel-municipios.png" });

  await page.goto("/dashboard?kpi=percentual_indigenas&nivel=uf");
  await expect(page.getByRole("group", { name: "Detalhar por" })).toHaveCount(0);
});

test("sobre os dados mostra release e licença", async ({ page }) => {
  await page.goto("/sobre");
  await expect(page.getByRole("heading", { name: "Release ativo" })).toBeVisible();
  await expect(page.getByText(/requires_review/).first()).toBeVisible();
});
