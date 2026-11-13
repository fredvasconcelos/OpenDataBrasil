import { expect, test } from "@playwright/test";

// Fluxo do critério de aceitação da Fase 5: pesquisar, abrir o indicador, filtrar
// território e período, ver gráfico e mapa, identificar a fonte e exportar.
test("pesquisa, painel, recorte por duplo clique, tooltip, seleção, limpeza e exportação", async ({ page }) => {
  await page.goto("/");
  // Início (DS v2.3): a busca ignora acentos; o indicador abre a prévia e dela vai ao painel.
  await page.getByLabel("Buscar indicador").fill("populacao residente");
  await page.getByRole("button", { name: "População residente (Censo)" }).first().click();
  const preview = page.getByRole("dialog");
  await expect(preview).toContainText("População residente (Censo)");
  await preview.getByRole("link", { name: "Abrir no painel" }).click();
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
  await page.getByRole("combobox", { name: /^Período/ }).selectOption("2010");
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
  // Serviços: transporte de passageiros e cargas (8695) ainda em preparação, sem
  // referência defensável para o tipo de índice (parte B adiada).
  const services = themes.filter({ has: page.locator(":scope > summary", { hasText: /^Serviços/ }) });
  await services.locator(":scope > summary").click();
  await services.locator("summary", { hasText: "Turismo e transportes" }).click();
  const planned = services.locator("li.planned").first();
  await expect(planned).toBeVisible();
  await expect(planned).toHaveAttribute("title", /tabela SIDRA 8695/);
  await expect(planned.locator("button")).toHaveCount(0);
  // Tooltip da evolução temporal (DS v2.3): período mais próximo do ponteiro e teclado.
  const plot = page.locator(".series-plot svg");
  // Abaixo de 1600 px o painel empilha: o gráfico fica na área central rolável.
  await plot.scrollIntoViewIfNeeded();
  const box = await plot.boundingBox();
  if (!box) throw new Error("gráfico da série sem caixa");
  await page.mouse.move(box.x + box.width - 30, box.y + box.height / 2);
  const tip = page.locator(".series-tip");
  await expect(tip).toBeVisible();
  await expect(tip).toContainText(/\d{3}\.\d{3}/);
  // O tooltip fica inteiro dentro do quadro do gráfico.
  const tipBox = await tip.boundingBox();
  expect(tipBox && tipBox.x + tipBox.width <= box.x + box.width + 1).toBe(true);
  await page.mouse.move(0, 0);
  await expect(tip).toBeHidden();
  await plot.focus();
  await page.keyboard.press("Home");
  await expect(tip).toBeVisible();
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
  // Rótulo limpo, sem a numeração da fonte (DS 2.3.6): "2.1.1 Alimentação" → "Alimentação".
  await expect(page.getByText(/(^|› )Alimentação( \(R\$\))?$/).first()).toBeAttached();
  // DS v2.3: muitas variáveis → tooltip em matriz (classes × despesas), inteiro na janela.
  const map = page.getByRole("img", { name: /Despesa média mensal familiar/ });
  await map.getByRole("button", { name: /^Bahia:/ }).hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toHaveClass(/matrix/);
  const box = await tooltip.boundingBox();
  const view = page.viewportSize();
  expect(box && view).toBeTruthy();
  if (box && view) {
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(view.width);
    expect(box.y + box.height).toBeLessThanOrEqual(view.height);
  }
  await page.screenshot({ path: "test-results/painel-pof-matriz.png", fullPage: false });
});

test("cabeçalho e rodapé (DS v2.3): GitHub, rodapé marinho e faixa fina no Painel", async ({ page }) => {
  await page.goto("/");
  const footer = page.locator("footer.footer");
  await expect(footer).toBeVisible();
  await expect(footer).not.toHaveClass(/slim/);
  await expect(footer.getByRole("link", { name: "Sobre os dados" })).toBeVisible();
  // O endereço do repositório vem do build (NEXT_PUBLIC_REPO_URL); sem valor, não aparece.
  const repo = page.getByRole("banner").getByRole("link", { name: "Repositório do projeto no GitHub" });
  if (await repo.count()) {
    await expect(repo).toHaveAttribute("href", /^https:\/\/github\.com\//);
    await expect(repo).toHaveAttribute("target", "_blank");
    await expect(footer.getByRole("link", { name: "Código no GitHub" })).toBeVisible();
  }
  await page.screenshot({ path: "test-results/inicio-rodape.png", fullPage: true });
  await page.goto("/dashboard?kpi=populacao_residente");
  await expect(footer).toHaveClass(/slim/);
  const height = await footer.evaluate((el) => el.getBoundingClientRect().height);
  expect(Math.round(height)).toBe(44);
  // O painel desconta a faixa: a página continua sem rolagem.
  const overflow = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("série mensal: IPCA com períodos formatados", async ({ page }) => {
  await page.goto("/dashboard?kpi=ipca");
  await expect(page.getByRole("heading", { level: 1, name: "IPCA" })).toBeVisible();
  // Período mais recente formatado como mês e ano (2026M09 → set 2026), não o código.
  await expect(page.locator(".crumb")).toContainText(/[a-z]{3} \d{4}/);
  // A série do IPCA no portal começa em 1998 (decisão do mantenedor; a Silver guarda 1979+).
  await expect(page.getByRole("combobox", { name: /^Período/ })).toContainText("jan 1998");
  await expect(page.getByRole("combobox", { name: /^Período/ })).not.toContainText("dez 1979");
  // Eixo de tempo: primeiro período ancorado no início; série longa rotula só os anos.
  const ticks = page.locator(".series-tick text");
  await expect(ticks.first()).toHaveText("jan 1998");
  await expect(ticks.nth(1)).toHaveText(/^\d{4}$/);
  const plot = page.locator(".series-plot svg");
  await plot.focus();
  await page.keyboard.press("End");
  await expect(page.locator(".series-tip-head")).toHaveText(/^[a-z]{3} \d{4}$/);
  await page.screenshot({ path: "test-results/painel-ipca-eixo-tempo.png", fullPage: false });
});

test("mapa em % de uma categoria (ADR-0010, decisão 16): municípios com Plano Diretor", async ({ page }) => {
  await page.goto("/dashboard?kpi=plano_diretor&nivel=uf");
  const map = page.getByRole("img", { name: /Plano Diretor/ });
  await expect(map.locator("path.territory")).toHaveCount(27);
  // A legenda diz o que o mapa mede: a parte da categoria no total de cada UF.
  const legend = map.locator("xpath=..").getByRole("group", { name: /Legenda: % Com Plano Diretor/ });
  await expect(legend).toBeVisible();
  await map.getByRole("button", { name: /^Rondônia:/ }).hover();
  await expect(page.getByRole("tooltip")).toContainText("Rondônia");
  await page.screenshot({ path: "test-results/painel-plano-diretor-pct.png", fullPage: false });
});

test("Início e Sobre (DS v2.3): etiquetas de tema, itens em preparação e filtro de situação", async ({ page }) => {
  await page.goto("/");
  const stats = page.locator(".home-stats");
  await expect(stats).toContainText("indicadores publicados");
  await expect(stats).toContainText("em preparação");
  // Etiqueta de tema filtra a lista; os itens em preparação aparecem sem ação.
  await page.locator(".theme-chip", { hasText: "Serviços" }).click();
  const chip = page.locator(".theme-chip", { hasText: "Serviços" });
  await expect(chip).toHaveAttribute("aria-pressed", "true");
  // Espera o fim da transição do fundo (120 ms) antes da captura.
  await page.mouse.move(0, 0);
  await expect(chip).not.toHaveCSS("background-color", "rgb(255, 255, 255)");
  const pending = page.locator(".kpi-pending", { hasText: "Volume e receita do transporte de passageiros e cargas" });
  await expect(pending).toBeVisible();
  await expect(pending).toHaveAttribute("title", /tabela SIDRA 8695/);
  await page.screenshot({ path: "test-results/inicio-tema-servicos.png", fullPage: false });
  // A busca acha pelo número da tabela.
  await page.locator(".theme-chip", { hasText: "Todos" }).click();
  await page.getByLabel("Buscar indicador").fill("6579");
  await expect(page.getByRole("button", { name: "População estimada" })).toBeVisible();
  await page.screenshot({ path: "test-results/inicio-busca-tabela.png", fullPage: false });

  await page.goto("/sobre");
  const status = page.getByRole("group", { name: "Situação" });
  await status.getByRole("button", { name: "Em preparação" }).click();
  await page.locator(".theme-chip", { hasText: "Serviços" }).click();
  const row = page.getByRole("button", { name: /Volume e receita do transporte de passageiros e cargas/ });
  await row.click();
  await expect(page.getByRole("link", { name: /8695/ })).toHaveAttribute("href", "https://sidra.ibge.gov.br/tabela/8695");
  await page.screenshot({ path: "test-results/sobre-em-preparacao.png", fullPage: false });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "test-results/sobre-topo.png", fullPage: false });

  // Tema escuro: as famílias de cor dos temas têm variante dark (tokens v2.3).
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator(".theme-grid")).toBeVisible();
  await page.screenshot({ path: "test-results/inicio-escuro.png", fullPage: false });
});

test("segurança pública (Sinesp VDE, MJSP): mapa municipal, série mensal e fonte", async ({ page }) => {
  await page.goto("/dashboard?kpi=sinesp_homicidio_doloso&nivel=uf");
  await expect(
    page.getByRole("heading", { level: 1, name: "Vítimas de homicídio doloso (registros policiais)" }),
  ).toBeVisible();
  const map = page.getByRole("img", { name: /homicídio doloso/ });
  await expect(map.locator("path.territory")).toHaveCount(27);
  // Fonte e licença de dados abertos do MJSP no rodapé do KPI.
  await expect(page.locator(".meta-source")).toContainText("MJSP · SINESP-VDE");
  await expect(page.locator(".meta-source")).not.toContainText("SIDRA");
  await expect(page.getByText(/mjsp-dados-abertos/).first()).toBeAttached();
  await page.screenshot({ path: "test-results/sinesp-homicidio-uf.png", fullPage: false });
  // Feminicídio: no Brasil, indisponível até 2018 (estados sem a tipificação).
  await page.goto("/dashboard?kpi=sinesp_feminicidio");
  const plot = page.locator(".series-plot svg");
  await plot.scrollIntoViewIfNeeded();
  await plot.focus();
  await page.keyboard.press("Home");
  await expect(page.locator(".series-tip")).toContainText("jan 2015");
  await expect(page.locator(".series-tip")).toContainText("…");
  await page.keyboard.press("End");
  await expect(page.locator(".series-tip")).toContainText(/\d/);
  await page.screenshot({ path: "test-results/sinesp-feminicidio-serie.png", fullPage: false });
});

test("busca da barra lateral fica fixa ao rolar a árvore de temas", async ({ page }) => {
  // Até 1599 px rola a barra inteira; em tela cheia, só a árvore (.themes).
  for (const [width, height, scroller] of [
    [1280, 720, ".sidebar"],
    [1920, 1080, ".sidebar .themes"],
  ] as const) {
    await page.setViewportSize({ width, height });
    await page.goto("/dashboard?kpi=populacao_estimada");
    const menu = page.getByRole("navigation", { name: "Temas e indicadores" });
    const search = page.getByLabel("Buscar tema ou indicador");
    // Abre temas até a árvore passar da altura da área que rola.
    const summaries = menu.locator(":scope > details:not([open]) > summary");
    for (let i = 0; i < 6; i++) await summaries.first().click();
    const area = page.locator(scroller);
    const overflow = await area.evaluate((el) => el.scrollHeight - el.clientHeight);
    expect(overflow).toBeGreaterThan(300);
    await area.evaluate((el) => el.scrollTo(0, el.scrollHeight));
    const areaBox = await area.boundingBox();
    const box = await search.boundingBox();
    if (!areaBox || !box) throw new Error("barra lateral sem caixa");
    // O campo continua dentro da área visível, logo abaixo do título fixo.
    expect(box.y).toBeGreaterThanOrEqual(areaBox.y - 1);
    expect(box.y).toBeLessThan(areaBox.y + 90);
    // Nenhum item da árvore aparece no recuo acima do bloco fixo.
    const above = await area.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const hit = document.elementFromPoint(r.x + r.width / 2, r.y + 4);
      return Boolean(hit?.closest("details"));
    });
    expect(above).toBe(false);
    // E está por cima da árvore: o ponto do meio do campo é o próprio campo.
    const onTop = await search.evaluate((el) => {
      const r = el.getBoundingClientRect();
      return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) === el;
    });
    expect(onTop).toBe(true);
    // E segue funcionando depois da rolagem.
    await search.fill("homicídio");
    await expect(menu.locator(".tree-status")).toContainText("indicador");
  }
});

test("trechos da busca lateral sem HTML da fonte (entidades e marcas)", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_estimada");
  await page.getByLabel("Buscar tema ou indicador").fill("Mortalidade");
  const snippets = page.locator(".tree-snippet");
  await expect(snippets.first()).toBeVisible();
  for (const text of await snippets.allInnerTexts()) {
    expect(text).not.toMatch(/&[a-z]+;|&#\d+;|<\/?[a-z]/i);
  }
  // Descrição da tabela 6606 (vítimas de homicídio): blocos da fonte separados por espaço.
  await page.getByLabel("Buscar tema ou indicador").fill("Mortalidade (SIM). Instituto");
  await expect(snippets.first()).toContainText("Mortalidade (SIM). Instituto");
});

test("óbitos por residência (SIM, Ministério da Saúde): mapa por UF, série desde 1996 e fonte", async ({ page }) => {
  await page.goto("/dashboard?kpi=sim_obitos_residencia&nivel=uf");
  await expect(page.getByRole("heading", { level: 1, name: "Óbitos por residência (SIM)" })).toBeVisible();
  const map = page.getByRole("img", { name: /Óbitos por residência/ });
  await expect(map.locator("path.territory")).toHaveCount(27);
  await expect(page.locator(".meta-source")).toContainText("MS · SIM-DORES");
  await expect(page.locator(".meta-source")).not.toContainText("SIDRA");
  const plot = page.locator(".series-plot svg");
  await plot.scrollIntoViewIfNeeded();
  await plot.focus();
  await page.keyboard.press("Home");
  await expect(page.locator(".series-tip")).toContainText("1996");
  await page.screenshot({ path: "test-results/sim-obitos-uf.png", fullPage: false });
});

test("grão de tempo (ADR-0013): Sinesp por ano soma os meses; ano incompleto sem valor", async ({ page }) => {
  await page.goto("/dashboard?kpi=sinesp_homicidio_doloso&nivel=uf");
  const grains = page.getByRole("group", { name: "Período por" });
  await expect(grains.getByRole("radio")).toHaveCount(4);
  // O rádio é controlado pela URL (estado compartilhável): clica e espera a URL.
  await grains.getByRole("radio", { name: "Ano" }).click();
  await expect(page).toHaveURL(/grao=ano/);
  await expect(grains.getByRole("radio", { name: "Ano" })).toBeChecked();
  await expect(grains).toContainText("valor derivado");
  // Sem período escolhido: o último ano completo (com os 12 meses).
  const period = page.getByRole("combobox", { name: /^Período/ });
  await expect(period).toHaveValue("2025");
  await expect(period.locator("option")).toContainText(["2015", "2026"]);
  const table = page.locator(".data-table");
  await expect(table.locator("tbody tr").first()).toContainText(/\d/);
  // 2026 só tem meses até setembro: o ano fica sem valor ("período incompleto").
  await period.selectOption("2026");
  await expect(table.locator("tbody")).toContainText("período incompleto");
  // Volta ao mês: o seletor de período lista meses de novo.
  await grains.getByRole("radio", { name: "Mês" }).click();
  await expect(page).not.toHaveURL(/grao=/);
  await expect(period.locator("option").first()).toHaveText("jan 2015");
  await page.screenshot({ path: "test-results/sinesp-grao-mes.png", fullPage: false });
});

test("grão de tempo: KPI de estoque ou anual não oferece o seletor", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_estimada");
  await expect(page.getByRole("combobox", { name: /^Período/ })).toBeVisible();
  await expect(page.getByRole("group", { name: "Período por" })).toHaveCount(0);
});

test("População por sexo e idade (9606): detalhe por idade em grupos quinquenais", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_sexo_idade&nivel=uf&dim=c287");
  await expect(page.getByRole("heading", { level: 1, name: "População por sexo e idade" })).toBeVisible();
  const head = page.locator(".data-table thead");
  await expect(head).toContainText("0 a 4 anos");
  await expect(head).toContainText("100 anos ou mais");
  // A fonte é a 9606 (a 9514 ficou só como conferência).
  await expect(page.locator(".meta-source")).toContainText("9606");
});

test("sexo no SIM e no Sinesp: classificações próprias com o rótulo Sexo", async ({ page }) => {
  await page.goto("/dashboard?kpi=sim_obitos_residencia&nivel=uf&dim=sexosim");
  const head = page.locator(".data-table thead");
  await expect(head).toContainText("Masculino");
  await expect(head).toContainText("Ignorado");
  await expect(page.getByRole("checkbox", { name: "Sexo" })).toBeChecked();
  await page.goto("/dashboard?kpi=sinesp_homicidio_doloso&nivel=uf&dim=sexosinesp");
  await expect(head).toContainText("Feminino");
  await expect(head).toContainText("Não informado");
  // Com o grão anual, o detalhe por sexo continua (soma dos meses por categoria).
  await page.goto("/dashboard?kpi=sinesp_homicidio_doloso&nivel=uf&dim=sexosinesp&grao=ano&periodo=2025");
  await expect(head).toContainText("Masculino");
  await expect(page.locator(".data-table tbody tr").first()).toContainText(/\d/);
});

test("POF em série (ADR-0016): 2002 a 2018 e só as faixas da edição na tabela", async ({ page }) => {
  await page.goto("/dashboard?kpi=despesa_familiar&nivel=regiao&dim=c339&periodo=2008");
  const head = page.locator(".data-table thead");
  // 2008: faixas de 2 a 25 SM de R$ 415; as de 2018 não aparecem.
  await expect(head).toContainText("Até 830 Reais");
  await expect(head).not.toContainText("Até 1.908 Reais");
  await page.goto("/dashboard?kpi=despesa_familiar&nivel=regiao&dim=c339&periodo=2018");
  await expect(head).toContainText("Até 1.908 Reais");
  await expect(head).not.toContainText("Até 830 Reais");
  await expect(page.getByRole("combobox", { name: /^Período/ })).toContainText("2002");
});

test("detalhes marginais (ADR-0016): uma dimensão por vez e POF antiga sem Brasil", async ({ page }) => {
  await page.goto("/dashboard?kpi=obitos&nivel=uf&dim=c1836,c244");
  await expect(page.getByText("Uma por vez: cada detalhe vem com os demais no Total.")).toBeVisible();
  const nature = page.getByRole("checkbox", { name: "Natureza do óbito" });
  const month = page.getByRole("checkbox", { name: "Mês de ocorrência" });
  await expect(nature).toBeChecked();
  await expect(month).not.toBeChecked();
  await month.click();
  await expect(page).toHaveURL(/dim=c244(&|$)/);
  await expect(nature).not.toBeChecked();
  await page.screenshot({ path: "test-results/detalhar-uma-por-vez.png", fullPage: false });
  await page.goto("/dashboard?kpi=pof_despesa_distribuicao_antiga");
  await expect(page.locator(".data-table tbody")).toContainText("Belém - PA");
  await expect(page.getByRole("heading", { name: /Total das áreas da POF/ })).toBeVisible();
});

test("agregação no tempo (ADR-0017): índice pela média, IPCA pelo último mês", async ({ page }) => {
  await page.goto("/dashboard?kpi=vendas_materiais&grao=ano&periodo=2024");
  await expect(page.getByText(/Média dos períodos publicados/)).toBeVisible();
  await page.goto("/dashboard?kpi=ipca&grao=ano&periodo=2024");
  await expect(page.getByText(/Valor do último período publicado/)).toBeVisible();
  await expect(page.locator(".data-table tbody")).toContainText("4,83");
});

test("escala do mapa sem colapso e unidade nas colunas (DS 2.3.6)", async ({ page }) => {
  // Esperança de vida (7362): UFs entre 72 e 82 anos; antes, "Até 80 · Mais de 80".
  await page.goto("/dashboard?kpi=esperanca_vida&nivel=uf");
  const legend = page.locator(".legend li");
  await expect(legend.first()).toBeVisible();
  expect(await legend.count()).toBeGreaterThanOrEqual(5);
  // Recorte do Nordeste: vários grupos, e não um só.
  await page.goto("/dashboard?kpi=esperanca_vida&nivel=uf&foco=regiao:2");
  await expect(legend.first()).toBeVisible();
  expect(await legend.count()).toBeGreaterThanOrEqual(4);
  await page.screenshot({ path: "test-results/escala-esperanca-vida-nordeste.png", fullPage: false });
  // Unidade no cabeçalho: POF de 1995 em % ("Total (%)").
  await page.goto("/dashboard?kpi=pof_despesa_distribuicao_antiga");
  await expect(page.locator(".data-table thead")).toContainText("Total (%)");
});
