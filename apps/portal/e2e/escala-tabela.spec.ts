import { expect, test, type Page } from "@playwright/test";

// DS 2.17 (pedido do mantenedor em 22/11/2026): em 1920 × 1080 o portal parecia grande
// demais (só ficava bom com zoom de 80%) e a tabela do Painel mostrava 2 linhas com Cor ou
// raça e nenhuma somando Sexo. A janela útil de um navegador em 1920 × 1080 tem ~1030 px.

const COR_SEXO = "/dashboard?kpi=populacao_residente&nivel=regiao&periodo=2022&dim=c86,c2";

async function tableRows(page: Page) {
  return page.locator(".pivot-wrap").evaluate((wrap) => {
    const box = wrap.getBoundingClientRect();
    const head = wrap.querySelector("thead")!.getBoundingClientRect();
    const rows = [...wrap.querySelectorAll("tbody tr")];
    const visible = rows.filter((tr) => {
      const r = tr.getBoundingClientRect();
      return r.top >= head.bottom - 1 && r.bottom <= box.bottom + 1;
    }).length;
    return { visible, total: rows.length, head: head.height, wrap: box.height };
  });
}

test("escala por largura: raiz em 13 px a partir de 1600 px, 15 px em notebook e 16 px no celular", async ({ page }) => {
  for (const [width, height, root] of [[1920, 1030, 13], [1536, 730, 15], [1366, 650, 15], [390, 844, 16]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    const size = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
    expect(size, `raiz em ${width} px`).toBeCloseTo(root, 1);
    // Piso de legibilidade: nenhum texto visível abaixo de 11 px.
    const smallest = await page.evaluate(() => {
      let min = Infinity;
      for (const el of document.querySelectorAll("body *")) {
        if (!(el instanceof HTMLElement) || !el.offsetParent || !el.childNodes.length) continue;
        if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent!.trim())) continue;
        min = Math.min(min, parseFloat(getComputedStyle(el).fontSize));
      }
      return min;
    });
    expect(smallest, `menor texto em ${width} px`).toBeGreaterThanOrEqual(11);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
});

test("tabela do Painel em 1920 × 1030: com Cor ou raça e Sexo todas as regiões aparecem", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1030 });
  await page.goto(COR_SEXO);
  await expect(page.locator(".pivot-table tbody tr").first()).toBeVisible();
  const rows = await tableRows(page);
  expect(rows.total).toBe(5);
  expect(rows.visible).toBe(5);
  // Período único fora do cabeçalho: ficam Cor ou raça e Sexo.
  await expect(page.locator(".pivot-table thead tr")).toHaveCount(2);
  expect(rows.head).toBeLessThan(rows.wrap * 0.3);
  // A página continua sem rolagem nessa largura (tela cheia do Painel).
  expect(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight + 1)).toBe(true);
  await page.screenshot({ path: "test-results/escala-tabela-1920-cor-sexo.png" });
});

test("tabela ampliada: abre por cima do painel, mostra mais linhas e fecha com Esc", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1030 });
  await page.goto("/dashboard?kpi=populacao_residente&nivel=uf&periodo=2022&dim=c86,c2");
  await expect(page.locator(".pivot-table tbody tr").first()).toBeVisible();
  const before = await tableRows(page);
  const toggle = page.getByRole("button", { name: "Ampliar tabela" });
  await toggle.click();
  await expect(page.getByRole("button", { name: "Reduzir tabela" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".area-table")).toHaveClass(/is-wide/);
  const wide = await tableRows(page);
  expect(wide.visible).toBeGreaterThan(before.visible);
  expect(wide.visible).toBeGreaterThanOrEqual(20);
  await page.screenshot({ path: "test-results/escala-tabela-ampliada.png" });
  await page.keyboard.press("Escape");
  await expect(page.locator(".area-table")).not.toHaveClass(/is-wide/);
  await expect(page.getByRole("button", { name: "Ampliar tabela" })).toBeFocused();
});

test("chips da tabela: rótulo, ‹ e × centralizados na mesma altura", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1030 });
  await page.goto(COR_SEXO);
  const chip = page.locator(".pivot-chip").filter({ hasText: "Sexo" });
  await expect(chip).toBeVisible();
  const centers = await chip.evaluate((el) => {
    const mid = (r: DOMRect) => r.top + r.height / 2;
    const box = el.getBoundingClientRect();
    const range = document.createRange();
    range.selectNodeContents(el.firstChild!);
    return {
      chip: mid(box),
      label: mid(range.getBoundingClientRect()),
      icons: [...el.querySelectorAll("svg")].map((s) => mid(s.getBoundingClientRect())),
    };
  });
  expect(centers.icons).toHaveLength(2);
  for (const c of [centers.label, ...centers.icons]) expect(Math.abs(c - centers.chip)).toBeLessThanOrEqual(1);
  // Mesma altura para chips, "+ campo", "Trocar" e o seletor do %.
  const heights = await page.locator(".pivot-chip, .pivot-zone select, .pivot-swap, .share-base select")
    .evaluateAll((els) => [...new Set(els.map((e) => Math.round(e.getBoundingClientRect().height)))]);
  expect(heights).toHaveLength(1);
  // DS 2.18 (referência do mantenedor): "Calcular % por" e a unidade à esquerda, sob
  // "Linhas"; só o botão i na borda direita da barra.
  const pos = await page.locator(".pivot-toolbar").evaluate((bar) => {
    const box = (sel: string) => bar.querySelector(sel)!.getBoundingClientRect();
    return { bar: bar.getBoundingClientRect(), rows: box(".pivot-zone"), share: box(".share-base label"), unit: box(".pivot-unit"), info: box(".info-button") };
  });
  expect(Math.abs(pos.share.left - pos.rows.left)).toBeLessThanOrEqual(1);
  expect(pos.unit.left - pos.share.right).toBeLessThanOrEqual(24);
  expect(Math.abs(pos.info.right - pos.bar.right)).toBeLessThanOrEqual(1);
});
