import { expect, test } from "@playwright/test";

import { openPeriods } from "./helpers";

// ADR-0026: período em árvore, vários períodos, Isolar por ano e Acumular.

test("vários períodos: uma coluna por período na tabela; o mapa mostra o último", async ({ page }) => {
  await page.goto("/dashboard?kpi=obitos_mensal&nivel=uf&grao=trimestre&periodo=2024T1");
  const tree = await openPeriods(page);
  // A caixa é controlada pela URL: clica e espera o estado (não usar check()).
  await tree.getByRole("checkbox", { name: "T2 2024", exact: true }).click();
  await expect(page).toHaveURL(/periodo=2024T1%2C2024T2/);
  const head = page.locator(".data-table thead");
  await expect(head).toContainText("T1 2024");
  await expect(head).toContainText("T2 2024");
  await expect(page.locator(".crumb")).toContainText("T1 2024 a T2 2024");
  // O ano marca todas as partes dele.
  await tree.getByRole("checkbox", { name: "2024", exact: true }).click();
  await expect(head).toContainText("T4 2024");
});

test("Acumular soma os períodos marcados no mapa e no gráfico; a tabela mostra cada um", async ({ page }) => {
  await page.goto("/dashboard?kpi=obitos_mensal&nivel=uf&grao=trimestre&periodo=2024T1,2024T2");
  const accumulate = page.getByRole("checkbox", { name: "Acumular" });
  await expect(accumulate).toBeEnabled();
  const map = page.waitForResponse((r) => r.url().includes("/map") && r.url().includes("accumulate=true"));
  await accumulate.click();
  await expect(page).toHaveURL(/acumular=1/);
  expect((await map).status()).toBe(200);
  await expect(page.locator(".crumb")).toContainText("(acumulado)");
  await expect(page.getByRole("heading", { name: /Evolução temporal.*\(acumulado\)/ })).toBeVisible();
  // A tabela nunca acumula (ADR-0026): um período por coluna e a explicação no botão i.
  const head = page.locator(".data-table thead");
  await expect(head).toContainText("T1 2024");
  await expect(head).toContainText("T2 2024");
  await page.getByRole("button", { name: "Sobre esta tabela" }).click();
  await expect(page.locator("#table-info")).toContainText("o acumulado aparece no mapa e no gráfico");
});

test("Isolar: o Período lista anos; barras por parte, uma por ano; acumulado no ano", async ({ page }) => {
  await page.goto("/dashboard?kpi=obitos_mensal&nivel=uf&grao=trimestre");
  await page.getByRole("checkbox", { name: "Isolar período" }).click();
  await expect(page).toHaveURL(/isolar=1/);
  const tree = await openPeriods(page);
  // Só anos: nenhum nó abre partes.
  await expect(tree.locator(".dim-filter-toggle")).toHaveCount(0);
  await expect(tree.getByRole("checkbox", { name: "2024", exact: true })).toBeChecked();
  await tree.getByRole("checkbox", { name: "2023", exact: true }).click();
  const legend = page.locator(".season-figure .series-legend");
  await expect(legend).toContainText("2023");
  await expect(legend).toContainText("2024");
  await expect(page.locator(".data-table thead")).toContainText("T4 2023");
  await page.getByRole("checkbox", { name: "Acumular" }).click();
  await expect(page.locator(".season-figure figcaption")).toContainText("acumulado no ano");
});

test("taxas não acumulam: a caixa fica desabilitada e a API recusa", async ({ page, request }) => {
  await page.goto("/dashboard?kpi=taxas_desocupacao&nivel=regiao");
  await expect(page.getByRole("checkbox", { name: "Acumular" })).toBeDisabled();
  const api = process.env.PORTAL_URL ?? "http://localhost:3000";
  const r = await request.get(`${api}/odb-api/kpis/taxas_desocupacao/map?level=uf&periods=2023T1,2023T2&accumulate=true`);
  expect(r.status()).toBe(422);
});

// DS 2.9: a "série completa" é a própria tabela com os períodos marcados (SIDRA 4099).
test("série no tempo: a tabela mostra todos os períodos marcados no filtro", async ({ page }) => {
  const pivot = page.waitForResponse(
    (r) => r.url().includes("/pivot") && r.url().includes("periods=2024T4%2C2025T1") && r.status() === 200,
  );
  await page.goto("/dashboard?kpi=taxas_desocupacao&nivel=regiao&periodo=2024T4,2025T1");
  await pivot;
  const head = page.locator(".data-table thead");
  await expect(head).toContainText("T4 2024");
  await expect(head).toContainText("T1 2025");
  await expect(page.getByRole("button", { name: "Série completa" })).toHaveCount(0);
});

test("exportar dados: janela com níveis, períodos e Selecionar tudo; arquivo longo com tipo", async ({ page }) => {
  await page.goto("/dashboard?kpi=taxas_desocupacao&nivel=regiao");
  await page.getByRole("button", { name: "Exportar dados…" }).click();
  const dialog = page.getByRole("dialog", { name: "Exportar dados" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("checkbox", { name: /Grande Região/ })).toBeChecked();
  await dialog.getByRole("button", { name: "Selecionar tudo" }).click();
  await expect(dialog.getByRole("checkbox", { name: /Ano/ })).toBeChecked();
  // Só Brasil e UF, todos os grãos, em JSON (para ler aqui).
  await dialog.getByRole("checkbox", { name: /Município/ }).click();
  await dialog.getByRole("checkbox", { name: /Grande Região/ }).click();
  await dialog.getByRole("radio", { name: "JSON" }).check();
  const download = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Baixar" }).click();
  const file = await download;
  const body = JSON.parse(await (await file.createReadStream())!.toArray().then((c) => Buffer.concat(c).toString()));
  const rows = body.dados ?? body.data ?? body.rows ?? body;
  const kinds = new Set((rows as { tipo: string }[]).map((r) => r.tipo));
  expect([...kinds].sort()).toEqual(["derivado", "publicado"]);
  await expect(dialog).toBeHidden();
});

// B6: tabela dinâmica.
test("tabela dinâmica: território × período, com Sexo nas linhas e troca de eixos", async ({ page }) => {
  await page.goto("/dashboard?kpi=populacao_residente&nivel=regiao&periodo=2010,2022");
  const table = page.locator(".pivot-table");
  await expect(table.locator("thead")).toContainText("2022");
  await expect(table.locator("tbody")).toContainText("Nordeste");
  await page.getByRole("combobox", { name: "Adicionar campo em Linhas" }).selectOption("c2");
  await expect(table.locator("tbody")).toContainText("Mulheres");
  await page.getByRole("button", { name: "Trocar linhas e colunas" }).click();
  await expect(table.locator("tbody")).toContainText("2010");
  await expect(table.locator("thead")).toContainText("Nordeste");
});
