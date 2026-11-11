import { expect, test } from "@playwright/test";

// Fluxo do critério de aceitação da Fase 5: pesquisar, abrir o indicador, filtrar
// território e período, ver gráfico e mapa, identificar a fonte e exportar.
test("pesquisa, painel, recorte por duplo clique, tooltip, seleção, limpeza e exportação", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Buscar indicador").fill("populacao residente");
  await page.getByRole("link", { name: "População residente (Censo)" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "População residente (Censo)" })).toBeVisible();

  // O mapa abre nas Grandes Regiões, sem dica nativa (<title>). Abaixo de 1600 px o
  // painel empilha e rola só a área central, nunca a página.
  const map = page.getByRole("img", { name: /População residente \(Censo\)/ });
  const inside = map.locator(".map-focus path.territory");
  const outside = map.locator("path.territory.context");
  await expect(inside).toHaveCount(5);
  await expect(outside).toHaveCount(0);
  await expect(map.locator("title")).toHaveCount(0);
  const overflow = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
  expect(overflow).toBeLessThanOrEqual(1);

  // Hover muda a cor dos itens do menu lateral e das abas do cabeçalho.
  const item = page.getByRole("button", { name: "População estimada" });
  const before = await item.evaluate((el) => getComputedStyle(el).backgroundColor);
  await item.hover();
  await expect.poll(() => item.evaluate((el) => getComputedStyle(el).backgroundColor)).not.toBe(before);
  const link = page.getByRole("link", { name: "Sobre os dados" });
  const linkBefore = await link.evaluate((el) => getComputedStyle(el).color);
  await link.hover();
  await expect.poll(() => link.evaluate((el) => getComputedStyle(el).color)).not.toBe(linkBefore);

  // Duplo clique no Nordeste: só ele se subdivide em UFs (9, coloridas); as outras
  // 4 regiões ficam em cinza, sem subdivisão. Tabela e trilha seguem o recorte.
  await map.getByRole("button", { name: /^Nordeste:/ }).dblclick();
  await expect(page).toHaveURL(/nivel=uf/);
  await expect(page).toHaveURL(/foco=regiao%3A2/);
  await expect(inside).toHaveCount(9);
  await expect(outside).toHaveCount(4);
  await expect(map.locator("path.focus-outline")).toHaveCount(1);
  const fill = (key: string) =>
    map.locator(`path[data-key="${key}"]`).evaluate((el) => getComputedStyle(el).fill);
  expect(await fill("regiao:3")).toBe(await fill("regiao:1"));
  expect(await fill("uf:29")).not.toBe(await fill("regiao:3"));
  await expect(page.getByText("Fora do recorte")).toBeVisible();
  // Legenda com título e grupos redondos: "Até …" na primeira ponta, "Mais de …" na última.
  const legend = map.locator("xpath=..").getByRole("group", { name: /Legenda: Pessoas/ });
  await expect(legend.getByText("Pessoas", { exact: true })).toBeVisible();
  await expect(legend.locator("li").first()).toHaveText(/^Até /);
  await expect(legend.locator("li").nth(-2)).toHaveText(/^Mais de /);
  const trail = page.getByRole("navigation", { name: "Recorte do mapa" });
  await expect(trail).toContainText("Nordeste");
  await expect(page.getByRole("heading", { name: /Dados · Estado \(UF\) · Nordeste · 2022/ })).toBeVisible();
  await expect(page.getByText("1–9 de 9")).toBeVisible();

  // Dimensões: cor ou raça > sexo, e tooltip no território sob o ponteiro.
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
  const box = await tooltip.boundingBox();
  expect((box?.y ?? 0) + (box?.height ?? 0)).toBeLessThanOrEqual(page.viewportSize()?.height ?? 0);
  await page.screenshot({ path: "test-results/painel-tooltip.png", fullPage: false });

  // Clique seleciona o território (sem contorno de foco): a série mostra a Bahia.
  await bahia.click();
  await expect(page).toHaveURL(/territorio=uf%3A29|territorio=uf:29/);
  expect(await bahia.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe("none");
  await expect(page.getByRole("heading", { name: /Evolução temporal · Bahia/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /Evolução temporal: Bahia/ })).toBeVisible();

  // Período.
  await page.getByLabel("Período").selectOption("2010");
  await expect(page.getByRole("heading", { name: /Dados · Estado \(UF\) · Nordeste · 2010/ })).toBeVisible();

  // Duplo clique na Bahia: seus 417 municípios coloridos; as outras 26 UFs em cinza.
  await map.getByRole("button", { name: /^Bahia:/ }).dblclick();
  await expect(page).toHaveURL(/nivel=municipio/);
  await expect(page).toHaveURL(/foco=uf%3A29/);
  await expect(inside).toHaveCount(417, { timeout: 30_000 });
  await expect(outside).toHaveCount(26);
  await expect(trail).toContainText("Nordeste");
  await expect(trail).toContainText("Bahia");
  await page.screenshot({ path: "test-results/painel-recorte-bahia.png", fullPage: false });

  // A trilha volta ao recorte de cima.
  await trail.getByRole("button", { name: "Nordeste" }).click();
  await expect(page).toHaveURL(/foco=regiao%3A2/);
  await expect(inside).toHaveCount(9);

  // Limpar filtros: Brasil inteiro nas regiões, sem recorte, dimensões, período ou território.
  await page.getByRole("button", { name: "Limpar filtros" }).click();
  await expect(page).toHaveURL(/nivel=regiao$/);
  await expect(inside).toHaveCount(5);
  await expect(outside).toHaveCount(0);
  await expect(page.getByLabel("Cor ou raça")).not.toBeChecked();
  await expect(page.getByRole("button", { name: "Limpar filtros" })).toBeDisabled();

  // Fonte visível no rodapé.
  await expect(page.getByText(/Tabela SIDRA 9606/)).toBeVisible();

  // Exportação CSV (ZIP com metadados).
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV" }).click();
  expect((await download).suggestedFilename()).toBe("populacao_residente_regiao.zip");
  await page.screenshot({ path: "test-results/painel-regioes.png", fullPage: true });
});

test("tela cheia (1920 × 1080): mapa à esquerda, gráfico e tabela à direita, sem rolagem", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/dashboard?kpi=populacao_residente&nivel=municipio&foco=uf%3A29");
  const map = page.getByRole("img", { name: /População residente/ });
  await expect(map.locator(".map-focus path.territory")).toHaveCount(417, { timeout: 30_000 });
  const scroll = await page.evaluate(() => {
    const main = document.querySelector(".main") as HTMLElement;
    return [document.documentElement.scrollHeight - innerHeight, main.scrollHeight - main.clientHeight];
  });
  expect(scroll[0]).toBeLessThanOrEqual(1);
  expect(scroll[1]).toBeLessThanOrEqual(1);
  const mapBox = await page.locator(".area-map").boundingBox();
  const chartBox = await page.locator(".area-chart").boundingBox();
  expect((chartBox?.x ?? 0) > (mapBox?.x ?? 0) + (mapBox?.width ?? 0) - 1).toBe(true);
  // Filtros na barra lateral; exportações junto do que exportam.
  await expect(page.locator(".sidebar .filters").getByLabel("Nível territorial")).toHaveValue("municipio");
  await expect(page.locator(".area-maphead").getByRole("button", { name: "PNG" })).toBeVisible();
  await expect(page.locator(".area-datahead").getByRole("button", { name: "CSV" })).toBeVisible();

  // Espera o enquadramento do recorte terminar (um clique interrompe a animação do d3-zoom).
  await page.waitForTimeout(800);
  // Clique num município do mapa: a tabela vai até a página dele e rola até a linha.
  await map.getByRole("button", { name: /^Ourolândia:/ }).click({ force: true });
  const row = page.locator('.area-table tr[aria-selected="true"]');
  await expect(row).toContainText("Ourolândia");
  await expect(page.locator(".pager")).not.toContainText(/^1–50 /);
  await expect
    .poll(async () => {
      const r = await row.boundingBox();
      const w = await page.locator(".area-table .table-wrap").boundingBox();
      return Boolean(r && w && r.y >= w.y && r.y + r.height <= w.y + w.height);
    })
    .toBe(true);
  await page.screenshot({ path: "test-results/painel-tela-cheia-localizar.png", fullPage: false });
});

test("roda do mouse abre e fecha recortes e descarta o tooltip do nível anterior", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_residente");
  const map = page.getByRole("img", { name: /População residente/ });
  const inside = map.locator(".map-focus path.territory");
  await expect(inside).toHaveCount(5);
  const sudeste = map.getByRole("button", { name: /^Sudeste:/ });
  const box = await sudeste.boundingBox();
  await page.mouse.move((box?.x ?? 0) + (box?.width ?? 0) / 2, (box?.y ?? 0) + (box?.height ?? 0) / 2);
  await expect(page.getByRole("tooltip")).toContainText("Sudeste");
  // Ponteiro parado sobre o Sudeste, só a roda: o recorte abre nele.
  for (let i = 0; i < 3; i++) await page.mouse.wheel(0, -200);
  await expect(page).toHaveURL(/foco=regiao%3A3/);
  await expect(inside).toHaveCount(4);
  await expect(map.locator("path.territory.context")).toHaveCount(4);
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  // Afastar volta ao Brasil inteiro.
  for (let i = 0; i < 3; i++) await page.mouse.wheel(0, 300);
  await expect(page).toHaveURL(/nivel=regiao/);
  await expect(page).not.toHaveURL(/foco=/);
  await expect(inside).toHaveCount(5);
});

test("recorte vindo da URL e tema escuro", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_residente&nivel=municipio&foco=uf%3A13");
  const map = page.getByRole("img", { name: /População residente/ });
  await expect(map.locator(".map-focus path.territory")).toHaveCount(62, { timeout: 30_000 });
  await expect(page.getByRole("navigation", { name: "Recorte do mapa" })).toContainText("Norte");
  await page.getByRole("button", { name: "Ativar tema escuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(map.locator(".map-focus path.territory")).toHaveCount(62, { timeout: 30_000 });
  await page.screenshot({ path: "test-results/painel-escuro-amazonas.png", fullPage: false });
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

test("panorama: 20 temas recolhidos, KPIs em preparação e tooltip da série", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_estimada");
  const menu = page.getByRole("navigation", { name: "Temas e indicadores" });
  const themes = menu.locator(":scope > details");
  await expect(themes).toHaveCount(20);
  // Só o tema do indicador atual fica aberto.
  await expect(menu.locator(":scope > details[open]")).toHaveCount(1);
  // Preços: só séries mensais, ainda em preparação (a Gold aceita só anos).
  const prices = themes.filter({ has: page.locator("summary", { hasText: "Preços" }) });
  await expect(prices.locator(":scope > summary")).toContainText("em preparação");
  await prices.locator(":scope > summary").click();
  await prices.locator("summary", { hasText: "Inflação ao consumidor" }).click();
  const planned = prices.locator("li.planned").first();
  await expect(planned).toBeVisible();
  await expect(planned).toHaveAttribute("title", /tabela SIDRA 1737/);
  await expect(planned.locator("button")).toHaveCount(0);
  // Tooltip da evolução temporal: valor do ponto ao passar o mouse.
  const point = page.getByTestId("series-point").last();
  await point.hover();
  await expect(page.locator(".chart-tip")).toBeVisible();
  await expect(page.locator(".chart-tip")).toContainText(/\d{3}\.\d{3}/);
});

test("KPI de Total gerado do panorama: mapa por UF, fonte e notas oficiais", async ({ page }) => {
  await page.goto("/dashboard?kpi=nascidos_vivos&nivel=uf");
  await expect(page.getByRole("heading", { level: 1, name: "Nascidos vivos" })).toBeVisible();
  const map = page.getByRole("img", { name: /Nascidos vivos/ });
  await expect(map.locator("path.territory")).toHaveCount(27);
  // Rodapé: tabela de origem e as limitações vindas das notas da tabela.
  await expect(page.getByText(/tabela SIDRA 2609/).first()).toBeAttached();
  await expect(page.getByText(/Fonte: IBGE/).first()).toBeAttached();
});

test("POF 6715 completa: classes de rendimento e despesas de consumo", async ({ page }) => {
  await page.goto("/dashboard?kpi=despesa_familiar&nivel=uf&dim=c339,c12190");
  await expect(
    page.getByRole("heading", { level: 1, name: "Despesa média mensal familiar" }),
  ).toBeVisible();
  await expect(page.getByText("Classes de rendimento").first()).toBeVisible();
  await expect(page.getByText("Despesas de consumo").first()).toBeVisible();
  await expect(page.getByText("2.1.1 Alimentação").first()).toBeAttached();
});
