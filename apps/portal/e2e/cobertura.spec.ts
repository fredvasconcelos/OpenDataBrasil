import { expect, test } from "@playwright/test";

function contrastOf(el: HTMLElement | SVGElement) {
  const css = getComputedStyle(el);
  const luminance = (color: string) => {
    const channels = color.match(/[\d.]+/g)!.slice(0, 3).map(v => {
      const s = Number(v) / 255;
      return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return channels[0]! * 0.2126 + channels[1]! * 0.7152 + channels[2]! * 0.0722;
  };
  const values = [luminance(css.color), luminance(css.backgroundColor)].sort((a, b) => a - b);
  return (values[1]! + 0.05) / (values[0]! + 0.05);
}
for (const theme of ["light", "dark"]) {
  test(`cobertura: amarelo, vermelho e neutro no tema ${theme}`, async ({ page }) => {
    await page.addInitScript(value => localStorage.setItem("odbr-theme", value), theme);
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto("/estatisticas/painel?kpi=despesa_familiar&nivel=municipio&periodo=2008");
    const yellow = page.getByRole("button", { name: "Aviso: dados parciais nesta tabela", exact: true });
    await expect(yellow).toBeVisible({ timeout: 30_000 });
    await expect(yellow).toHaveAttribute("aria-expanded", "false");
    await expect(yellow).toHaveClass(/is-warning/);
    await yellow.focus();
    await page.keyboard.press("Enter");
    const warning = page.locator(".table-alert.is-warning");
    await expect(warning).toContainText("2008");
    await expect(warning).toContainText(/26 de 5[.\s]564 territórios/);
    await expect(warning.getByRole("link", { name: "1594", exact: true })).toHaveAttribute("href", "https://sidra.ibge.gov.br/tabela/1594");
    await expect(page.locator(".pivot-table tbody tr")).toHaveCount(26);
    await page.screenshot({ path: `test-results/cobertura-${theme}-amarelo.png`, fullPage: true });
    // Contraste do ícone contra o próprio botão; a forma e o nome também diferem.
    const contrast = await yellow.evaluate(contrastOf);
    expect(contrast).toBeGreaterThanOrEqual(3);
    await yellow.click();
    await expect(yellow).toHaveAttribute("aria-expanded", "false");

    await page.goto("/estatisticas/painel?kpi=migrantes_uf&nivel=municipio&foco=uf%3A25&periodo=2022&dim=c2083");
    const red = page.getByRole("button", { name: "Aviso: detalhe indisponível nesta tabela", exact: true });
    await expect(red).toHaveAttribute("aria-expanded", "true", { timeout: 30_000 });
    await expect(red).toHaveClass(/is-danger/);
    expect(await red.evaluate(contrastOf)).toBeGreaterThanOrEqual(3);
    await expect(page.locator(".table-alert.is-danger")).toContainText("a fonte não publica este detalhe por Município");
    await expect(page.locator(".pivot-table tbody tr")).toHaveCount(223);
    await page.screenshot({ path: `test-results/cobertura-${theme}-vermelho.png`, fullPage: true });

    await page.goto("/estatisticas/painel?kpi=populacao_residente&nivel=uf&periodo=2022");
    const neutral = page.getByRole("button", { name: "Sobre esta tabela", exact: true });
    await expect(neutral).toHaveAttribute("aria-expanded", "false", { timeout: 30_000 });
    await expect(neutral).not.toHaveClass(/is-warning|is-danger/);
    await page.screenshot({ path: `test-results/cobertura-${theme}-neutro.png`, fullPage: true });
  });
}

const samples = [
  ["despesa_familiar", "municipio", "2008", ""],
  ["migrantes_uf", "municipio", "2022", "c2083"],
  ["esgotamento_serie", "uf", "2025", "c1"],
  ["pof_despesa_alimentacao_antiga", "regiao_metropolitana", "1995", ""],
  ["populacao_residente", "uf", "2022", "c2"],
  ["ipca", "uf", "2026M10", ""],
  ["obitos_mensal", "uf", "2024", ""],
  ["plano_diretor", "municipio", "2021", "c12446"],
  ["abate_bovinos", "regiao", "1997T1", "c18"],
  ["seguranca_alimentar", "uf", "2024", "c12404"],
  ["sim_obitos_residencia", "municipio", "2022", "sexosim"],
] as const;

for (const [kpi, level, period, dimension] of samples) {
  test(`inventário: amostra ${kpi} no portal real`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const params = new URLSearchParams({ kpi, nivel: level, periodo: period });
    if (dimension) params.set("dim", dimension);
    if (kpi === "obitos_mensal") params.set("grao", "ano");
    if (level === "municipio" && kpi !== "despesa_familiar") params.set("foco", "uf:25");
    await page.goto(`/estatisticas/painel?${params}`);
    await expect(page.locator(".pivot-table")).toBeVisible({ timeout: 30_000 });
    await expect(page.locator(".pivot-table tbody tr").first()).toBeVisible();
    await expect(page.locator(".area-table .error")).toHaveCount(0);
    expect(errors).toEqual([]);
    await page.screenshot({ path: `test-results/cobertura-amostra-${kpi}.png`, fullPage: true });
  });
}

test("cobertura: detalhe só com Total mostra V2 e conserva o valor", async ({ page }) => {
  await page.goto("/estatisticas/painel?kpi=afazeres_domesticos&nivel=brasil&periodo=2016&dim=c2");
  await expect(page.getByRole("button", { name: "Aviso: detalhe indisponível nesta tabela", exact: true })).toHaveAttribute("aria-expanded", "true", { timeout: 30_000 });
  await expect(page.locator(".table-alert.is-danger")).toContainText("a tabela mostra só o Total");
  await expect(page.locator(".pivot-table tbody tr")).toHaveCount(1);
  await page.screenshot({ path: "test-results/cobertura-v2-total.png", fullPage: true });
});
