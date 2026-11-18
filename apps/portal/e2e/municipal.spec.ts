import { expect, test } from "@playwright/test";

import { openPeriods } from "./helpers";

// Amostras conferidas em consultas reais à API SIDRA em 2026-11-15.
// A POF municipal só existe em 2008; a PNAD usa os quatro grupos nativos da 7270.
const cases = [
  {
    id: "indigenas_em_terras_indigenas",
    label: "Pessoas indígenas em terras indígenas",
    period: "2022",
    geography: "municipio:1303809",
    focus: "uf:13",
    value: 24892,
  },
  {
    id: "despesa_familiar",
    label: "Despesa média mensal familiar",
    period: "2008",
    geography: "municipio:3550308",
    focus: "uf:35",
    value: 4030.71,
  },
  {
    id: "nivel_instrucao_capitais",
    label: "Nível de instrução em quatro grupos (PNAD)",
    period: "2025",
    geography: "municipio:3550308",
    focus: "uf:35",
    // O mapa deste KPI mostra o percentual do primeiro grupo: 1452 / 8358 × 100.
    value: 17.37,
  },
];

for (const sample of cases) {
  test(`cobertura municipal: ${sample.label}`, async ({ page }) => {
    const response = page.waitForResponse((r) => {
      const url = new URL(r.url());
      return url.pathname === `/odb-api/kpis/${sample.id}/map`
        && url.searchParams.get("level") === "municipio"
        && r.status() === 200;
    });
    const query = new URLSearchParams({
      kpi: sample.id,
      nivel: "municipio",
      periodo: sample.period,
      territorio: sample.geography,
      foco: sample.focus,
    });
    await page.goto(`/dashboard?${query}`);
    await expect(page.getByRole("heading", { level: 1, name: sample.label, exact: true })).toBeVisible();
    const data = await (await response).json();
    expect(data.period).toBe(sample.period);
    expect(data.values.find((v: { geography_key: string }) => v.geography_key === sample.geography)?.value)
      .toBe(sample.value);
    const map = page.getByRole("img", { name: new RegExp(sample.label.replace(/[()]/g, "\\$&")) });
    await expect(map.locator(`path[data-key="${sample.geography}"]`)).toBeVisible();
    await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
    await page.screenshot({ path: `test-results/municipal-${sample.id}.png` });
  });
}

test("plano de seca: detalhe municipal disponível sem o recorte por porte", async ({ page }) => {
  const response = page.waitForResponse((r) => {
    const url = new URL(r.url());
    return url.pathname === "/odb-api/kpis/plano_seca/detail"
      && url.searchParams.get("geography") === "municipio:3550308"
      && url.searchParams.get("dimensions") === "c1347"
      && r.status() === 200;
  });
  await page.goto(
    "/dashboard?kpi=plano_seca&nivel=municipio&periodo=2020&territorio=municipio%3A3550308&foco=uf%3A35&dim=c1347",
  );
  await expect(page.getByRole("checkbox", {
    name: "Plano para a seca", exact: true,
  })).toBeChecked();
  await expect(page.getByRole("checkbox", {
    name: "Tamanho do município só Brasil, Grande Região, Estado (UF)", exact: true,
  })).toBeDisabled();
  await page.getByRole("img", { name: /Municípios atingidos pela seca/ })
    .getByRole("button", { name: /^São Paulo:/ }).focus();
  const data = await (await response).json();
  const parts = new Map(data.root.children.map((c: { category_key: string; value: number }) =>
    [c.category_key, c.value]));
  expect(parts.get("c1347:57253")).toBe(0);
  expect(parts.get("c1347:57254")).toBe(1);
  await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
  await page.screenshot({ path: "test-results/municipal-plano-seca.png" });
});

for (const id of ["esgotamento_serie", "lixo_serie", "alfabetizacao_serie", "despesa_familiar"]) {
  test(`calendário municipal abre em período publicado: ${id}`, async ({ page }) => {
    const period = id === "despesa_familiar" ? "2008" : "2022";
    const response = page.waitForResponse((r) => {
      const url = new URL(r.url());
      return url.pathname === `/odb-api/kpis/${id}/map`
        && url.searchParams.get("level") === "municipio"
        && r.status() === 200;
    });
    await page.goto(`/dashboard?kpi=${id}&nivel=municipio`);
    const data = await (await response).json();
    expect(data.period).toBe(period);
    expect(data.values.length).toBeGreaterThan(0);
    // Só anos com cobertura municipal; o mais recente começa marcado (ADR-0026).
    const selector = await openPeriods(page);
    await expect(selector.getByRole("checkbox", { name: period, exact: true })).toBeChecked();
    await expect(selector.locator(".period-tree > ul > li"))
      .toHaveCount(id === "alfabetizacao_serie" ? 2 : 1);
    if (id === "alfabetizacao_serie") {
      await expect(selector.getByRole("checkbox", { name: "2010", exact: true }))
        .not.toBeChecked();
    }
    await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
  });
}

test("trocar UF por município na POF remove da URL o ano sem cobertura", async ({ page }) => {
  await page.goto("/dashboard?kpi=despesa_familiar&nivel=uf&periodo=2018");
  const tree = await openPeriods(page);
  await expect(tree.getByRole("checkbox", { name: "2018", exact: true })).toBeChecked();
  await page.getByRole("combobox", { name: "Nível territorial", exact: true }).selectOption("municipio");
  await expect(tree.getByRole("checkbox", { name: "2008", exact: true })).toBeChecked();
  await expect(page).not.toHaveURL(/periodo=2018/);
  await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
});
