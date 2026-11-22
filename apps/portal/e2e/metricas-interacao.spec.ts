import { expect, test } from "@playwright/test";

// Respostas isoladas: não gravam métricas sintéticas no banco em uso.
test.beforeEach(async ({ page }) => {
  const period = { from: "2020-01-01", to: "2026-11-18" };
  const place = (geography_key: string, name: string, views: number, share_pct: number) =>
    ({ geography_key, name, views, share_pct, status: "ok" });
  await page.route("**/odb-api/metrics/**", async route => {
    const url = new URL(route.request().url());
    expect(url.searchParams.get("period")).toBe("all");
    let body: unknown;
    if (url.pathname.endsWith("/summary")) {
      body = { period, collection_started_at: "2020-01-01T00:00:00-03:00", generated_at: "2026-11-18T12:00:00Z", views: 200, downloads: 20, kpi_opens: 50, countries: 3, api_calls: null };
    } else if (url.pathname.endsWith("/datasets")) {
      body = { period, sort: url.searchParams.get("sort"), items: [{ kpi_id: "populacao_estimada", title: "População estimada", theme: "População e demografia", views: 50, downloads: 20, api_calls: null }] };
    } else {
      const level = url.searchParams.get("level");
      const items = level === "pais"
        ? [place("pais:BR", "Brasil", 100, 50), place("pais:US", "Estados Unidos", 80, 40), place("pais:ES", "Espanha", 20, 10)]
        : level === "uf" ? [place("uf:35", "São Paulo", 60, 60), place("uf:33", "Rio de Janeiro", 30, 30), place("uf:0", "Estado não identificado", 10, 10)] : [];
      body = { period, level, within: url.searchParams.get("within"), items };
    }
    await route.fulfill({ json: body });
  });
});

test("Métricas: globo parado, roda revela estados, percentuais nacionais e recorte", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/metricas");
  await expect(page.locator(".metrics-summary")).not.toContainText("Desde o início");
  await expect(page.getByRole("heading", { name: "Como contamos", exact: true })).toHaveCount(0);
  const mapPanel = page.locator(".metrics-map-panel");
  const firstRanking = page.locator(".metrics-rankings > section").first();
  await expect(mapPanel).toHaveCSS("background-color", "rgb(255, 255, 255)");
  expect(await mapPanel.evaluate(element => getComputedStyle(element).padding)).toBe(
    await firstRanking.evaluate(element => getComputedStyle(element).padding),
  );
  const panelBox = await mapPanel.boundingBox();
  const rankingBox = await firstRanking.boundingBox();
  expect(Math.abs(panelBox!.y - rankingBox!.y)).toBeLessThanOrEqual(1);
  expect(await page.locator(".metrics-cards > div").first().evaluate(element => getComputedStyle(element).backgroundColor)).toBe("rgba(0, 0, 0, 0)");
  const map = page.locator(".access-map-surface");
  const globe = map.locator("svg").first();
  await expect(map.getByRole("button", { name: "Brasil: 100 visualizações", exact: true })).toBeVisible();
  await expect(page.getByRole("group", { name: "Período" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Aproximar", exact: true })).toHaveCount(0);
  await map.getByRole("button", { name: "Brasil: 100 visualizações", exact: true }).hover();
  await expect(map.getByRole("tooltip")).toContainText("50,0% do total global");
  await expect(map.getByRole("tooltip")).not.toContainText("2020");
  const before = await globe.locator("path").nth(1).getAttribute("d");
  await page.waitForTimeout(250);
  expect(await globe.locator("path").nth(1).getAttribute("d")).toBe(before);
  const surfaceBounds = await globe.boundingBox();
  await page.mouse.move(surfaceBounds!.x + 100, surfaceBounds!.y + 100);
  await page.mouse.down({ button: "right" });
  await page.mouse.move(surfaceBounds!.x + 140, surfaceBounds!.y + 100);
  await page.mouse.up({ button: "right" });
  expect(await globe.locator("path").nth(1).getAttribute("d")).toBe(before);
  await page.mouse.down({ button: "left" });
  await page.mouse.move(surfaceBounds!.x + 190, surfaceBounds!.y + 120, { steps: 5 });
  await page.mouse.up({ button: "left" });
  expect(await globe.locator("path").nth(1).getAttribute("d")).not.toBe(before);
  await globe.focus();
  await page.keyboard.press("Home");
  await globe.hover();
  await page.mouse.wheel(0, -700);
  await expect(map.getByRole("button", { name: "São Paulo: 60 visualizações", exact: true })).toBeVisible();
  await map.getByRole("button", { name: "São Paulo: 60 visualizações", exact: true }).hover();
  await expect(map.getByRole("tooltip")).toContainText("60,0% do total do Brasil");
  const bounds = await map.boundingBox();
  const tooltip = await map.getByRole("tooltip").boundingBox();
  expect(tooltip!.x).toBeGreaterThanOrEqual(bounds!.x);
  expect(tooltip!.x + tooltip!.width).toBeLessThanOrEqual(bounds!.x + bounds!.width);
  const rankings = await page.locator(".metrics-rankings").boundingBox();
  expect(rankings!.x).toBeGreaterThan(bounds!.x + bounds!.width);
  await page.screenshot({ path: "test-results/metricas-desktop.png", fullPage: true });
  await globe.focus();
  await page.keyboard.press("Home");
  await expect(map.getByRole("button", { name: "Brasil: 100 visualizações", exact: true })).toBeVisible();
  await expect(map.getByRole("button", { name: "São Paulo: 60 visualizações", exact: true })).toHaveCount(0);
  const brazil = map.getByRole("button", { name: "Brasil: 100 visualizações", exact: true });
  await brazil.focus();
  await page.keyboard.press("Enter");
  await expect(brazil).toHaveAttribute("aria-pressed", "true");
});

test("Métricas: celular mantém cartões e rankings sem rolagem horizontal", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/metricas");
  await expect(page.locator(".access-map")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "test-results/metricas-celular.png", fullPage: true });
});


test("Métricas: rankings iguais alinham a base do mapa e contêm listas extensas", async ({ page }) => {
  await page.route("**/odb-api/metrics/datasets**", route => {
    const sort = new URL(route.request().url()).searchParams.get("sort");
    return route.fulfill({ json: {
      period: { from: "2020-01-01", to: "2026-11-18" }, sort,
      items: Array.from({ length: 50 }, (_, i) => ({
        kpi_id: `exemplo-${i}`, title: `Indicador de teste com título extenso ${i}`,
        theme: "Tema de teste", views: 100 - i, downloads: 50 - i, api_calls: null,
      })),
    } });
  });
  await page.goto("/metricas");
  await expect(page.locator(".metrics-rankings > section")).toHaveCount(3);
  await expect(page.locator(".top-datasets tbody tr")).toHaveCount(100);
  for (const width of [1920, 1366, 1060]) {
    await page.setViewportSize({ width, height: 1080 });
    const map = await page.locator(".metrics-map-panel").boundingBox();
    const cards = await page.locator(".metrics-rankings > section").evaluateAll(elements =>
      elements.map(element => {
        const box = element.getBoundingClientRect();
        return { top: box.top, bottom: box.bottom, height: box.height };
      }),
    );
    expect(Math.abs(cards[0]!.top - map!.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(cards[2]!.bottom - map!.y - map!.height)).toBeLessThanOrEqual(1);
    expect(Math.max(...cards.map(c => c.height)) - Math.min(...cards.map(c => c.height))).toBeLessThanOrEqual(1);
    const gaps = [cards[1]!.top - cards[0]!.bottom, cards[2]!.top - cards[1]!.bottom];
    expect(Math.abs(gaps[0]! - gaps[1]!)).toBeLessThanOrEqual(1);
    // DS 2.17: 24 px de referência (1,5rem), escalados pela raiz da largura atual.
    const root = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
    expect(gaps[0]).toBeCloseTo((24 * root) / 16, 0);
    expect(await page.locator(".metrics-rankings > section").nth(1).evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
  }
});

test("Métricas: roda mantém o país sob o cursor e não revela UFs em outro continente", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/metricas");
  const map = page.locator(".access-map-surface");
  const point = map.getByRole("button", { name: "Estados Unidos: 80 visualizações", exact: true });
  await expect(point).toBeVisible();
  const before = await point.boundingBox();
  // Chrome arredonda as coordenadas do ponteiro; medir o ponto geográfico relativo
  // à posição efetiva do evento evita confundir esse arredondamento com deriva.
  await map.evaluate(element => element.addEventListener("wheel", event => {
    const wheel = event as WheelEvent;
    (element as HTMLElement).dataset.testAnchor = JSON.stringify([wheel.clientX, wheel.clientY]);
  }, { once: true, capture: true }));
  const sphere = map.locator("svg path").first();
  const previous = await sphere.getAttribute("d");
  await point.hover();
  await page.mouse.wheel(0, -700);
  await expect.poll(() => sphere.getAttribute("d")).not.toBe(previous);
  const after = await point.boundingBox();
  const anchor = JSON.parse(await map.getAttribute("data-test-anchor") ?? "[]") as [number, number];
  const factor = Math.exp(700 * 0.002);
  expect(Math.abs(after!.x + after!.width / 2 - anchor[0] - (before!.x + before!.width / 2 - anchor[0]) * factor)).toBeLessThanOrEqual(1);
  expect(Math.abs(after!.y + after!.height / 2 - anchor[1] - (before!.y + before!.height / 2 - anchor[1]) * factor)).toBeLessThanOrEqual(1);
  await expect(map.getByRole("button", { name: "São Paulo: 60 visualizações", exact: true })).toHaveCount(0);
});

test("Métricas: gesto de pinça aproxima e retorna sem deixar pontos fora do mapa", async ({ page, context }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/metricas");
  const map = page.locator(".access-map-surface");
  await expect(map.getByRole("button", { name: "Brasil: 100 visualizações", exact: true })).toBeVisible();
  await map.scrollIntoViewIfNeeded();
  const box = await map.boundingBox();
  const cdp = await context.newCDPSession(page);
  const center = { x: box!.x + box!.width / 2, y: box!.y + box!.height / 2 };
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [
    { id: 0, x: center.x - 15, y: center.y }, { id: 1, x: center.x + 15, y: center.y },
  ] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [
    { id: 0, x: center.x - 60, y: center.y }, { id: 1, x: center.x + 60, y: center.y },
  ] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await expect(map.getByRole("button", { name: "São Paulo: 60 visualizações", exact: true })).toBeVisible();
  for (const point of await map.locator(".access-point").all()) {
    const rect = await point.boundingBox();
    expect(rect!.x).toBeGreaterThanOrEqual(box!.x);
    expect(rect!.x + rect!.width).toBeLessThanOrEqual(box!.x + box!.width);
  }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [
    { id: 0, x: center.x - 60, y: center.y }, { id: 1, x: center.x + 60, y: center.y },
  ] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [
    { id: 0, x: center.x - 15, y: center.y }, { id: 1, x: center.x + 15, y: center.y },
  ] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await expect(map.getByRole("button", { name: "Brasil: 100 visualizações", exact: true })).toBeVisible();
  await expect(map.getByRole("button", { name: "São Paulo: 60 visualizações", exact: true })).toHaveCount(0);

});
