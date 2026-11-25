import { expect, test } from "@playwright/test";

import { expectPlainInfo } from "./helpers";

const url = "/estatisticas/painel?kpi=sinesp_feminicidio&nivel=regiao&grao=semestre&periodo=2023%2C2024%2C2025&acumular=1&territorio=uf%3A25&isolar=1";

for (const theme of ["light", "dark"]) {
  for (const size of [{ width: 1920, height: 1080 }, { width: 1920, height: 720 }, { width: 390, height: 844 }]) {
    test(`método no i sem sobreposição: ${theme} ${size.width}x${size.height}`, async ({ page }) => {
      await page.setViewportSize(size);
      await page.addInitScript(value => localStorage.setItem("odbr-theme", value), theme);
      await page.goto(url);
      if (size.width < 992) await page.getByRole("button", { name: "Série", exact: true }).click();
      const chart = page.getByRole("region", { name: /Evolução temporal/ });
      await expect(chart.locator(".season-bar")).toHaveCount(2);
      await expect(chart.getByRole("heading", { level: 2 })).toContainText("Paraíba");
      const button = chart.getByRole("button", { name: "Sobre o método do gráfico", exact: true });
      await expect(button).toHaveAttribute("aria-expanded", "false");
      await expect(chart.locator(".chart-info")).toHaveCount(0);
      // A área flexível precisa conter o SVG, inclusive no quadro de tela larga.
      await expect.poll(() => chart.locator(".series-plot").evaluate(el => {
        const box = el.getBoundingClientRect(), svg = el.querySelector("svg")!.getBoundingClientRect();
        return box.height >= 80 && svg.bottom <= box.bottom + 1;
      })).toBe(true);
      await chart.screenshot({ path: `test-results/metodo-fechado-${theme}-${size.width}x${size.height}.png` });
      await button.focus();
      await page.keyboard.press("Enter");
      const info = chart.getByRole("note", { name: "Como ler este gráfico", exact: true });
      await expect(info).toBeVisible();
      await expect(info).toContainText("entre 2023 e 2025");
      await expect(info).toContainText("tabela e as exportações preservam os períodos separados");
      const bounds = await info.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(size.width);
      await page.screenshot({ path: `test-results/metodo-aberto-${theme}-${size.width}x${size.height}.png`, fullPage: true });
      await page.keyboard.press("Escape");
      await expect(button).toBeFocused();
      await expect(info).toHaveCount(0);
    });
  }
}

test("indisponibilidade vermelha abre o método automaticamente e permite fechar", async ({ page }) => {
  await page.route("**/odb-api/kpis/sinesp_feminicidio/seasonal?**", async route => {
    const response = await route.fetch();
    const data = await response.json();
    const point = data.series[0].points[0];
    // Simula a resposta de indisponibilidade; os valores reais não são alterados.
    Object.assign(point, { value: null, status: "absent", severity: "danger", present: 0,
      missing: point.contributors, contributors: [] });
    await route.fulfill({ response, json: data });
  });
  await page.goto(url);
  const chart = page.getByRole("region", { name: /Evolução temporal/ });
  const button = chart.getByRole("button", { name: "Sobre o método do gráfico: dados indisponíveis", exact: true });
  await expect(button).toHaveClass(/is-danger/);
  await expect(button).toHaveAttribute("aria-expanded", "true");
  await expect(chart.getByRole("alert")).toContainText("Sem valor disponível para:");
  await button.click();
  await expect(button).toHaveAttribute("aria-expanded", "false");
});


for (const theme of ["light", "dark"]) {
  test(`i sem elipse e meses sem valor no trimestre: ${theme}`, async ({ page }) => {
    await page.addInitScript(value => localStorage.setItem("odbr-theme", value), theme);
    await page.goto("/estatisticas/painel?kpi=sinesp_feminicidio&nivel=uf&grao=trimestre&periodo=2026&acumular=1&territorio=uf%3A25&isolar=1");
    const chart = page.getByRole("region", { name: /Evolução temporal/ });
    const red = chart.getByRole("button", { name: "Sobre o método do gráfico: dados indisponíveis", exact: true });
    await expect(red).toHaveAttribute("aria-expanded", "true");
    await expectPlainInfo(red);
    await expect(chart.getByRole("alert").locator("li")).toHaveText(
      "T4 · Total: Sem valor disponível para: out 2026, nov 2026, dez 2026.",
    );
    await expect(chart.getByRole("alert")).not.toContainText(/parcela|Nenhuma das/i);
    await chart.scrollIntoViewIfNeeded();
    await page.screenshot({ path: `test-results/icone-vermelho-${theme}.png`, fullPage: true });
    await page.goto("/estatisticas/painel?kpi=sinesp_homicidio_doloso&nivel=uf&grao=trimestre&periodo=2023,2026&acumular=1&territorio=uf%3A25&isolar=1");
    const yellow = page.getByRole("button", { name: "Sobre o método do gráfico: dados parciais", exact: true });
    await expect(yellow).toHaveAttribute("aria-expanded", "false");
    await yellow.hover();
    await expectPlainInfo(yellow);
    await yellow.click();
    await expectPlainInfo(yellow);
    await expect(page.locator(".seasonal-alerts")).toContainText("9 de 12 períodos com valor");
    await page.locator(".area-chart").scrollIntoViewIfNeeded();
    await page.screenshot({ path: `test-results/icone-amarelo-${theme}.png`, fullPage: true });
  });
}
