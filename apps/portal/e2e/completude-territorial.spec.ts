import { expect, test } from "@playwright/test";

type MapValue = { geography_key: string; value: number | null; status: string };

// Composição da DTB 2025 fixada na Gold: Norte, Nordeste, Sudeste, Sul e Centro-Oeste.
const stateCounts: Record<string, number> = { "1": 7, "2": 9, "3": 4, "4": 3, "5": 4 };

for (const sample of [
  { id: "sim_obitos_residencia", period: "2024" },
  { id: "abate_bovinos", period: "2026T2" },
  { id: "leite_adquirido", period: "2026T2" },
  { id: "ovos_produzidos", period: "2026T2" },
]) {
  test(`região derivada com cobertura e sigilo: ${sample.id}`, async ({ page, request }) => {
    const statesResponse = await request.get(
      `/odb-api/kpis/${sample.id}/map?level=uf&period=${sample.period}`,
    );
    expect(statesResponse.ok()).toBeTruthy();
    const states: MapValue[] = (await statesResponse.json()).values;
    const regionsResponse = await request.get(
      `/odb-api/kpis/${sample.id}/map?level=regiao&period=${sample.period}`,
    );
    expect(regionsResponse.ok()).toBeTruthy();
    const regions: MapValue[] = (await regionsResponse.json()).values;
    expect(regions).toHaveLength(5);
    for (const [code, count] of Object.entries(stateCounts)) {
      const components = states.filter((v) => v.geography_key.startsWith(`uf:${code}`));
      const region = regions.find((v) => v.geography_key === `regiao:${code}`)!;
      const available = components.filter((v) =>
        v.value !== null && ["valid", "rounded_zero", "true_zero"].includes(v.status));
      const complete = components.length === count && available.length === count;
      if (complete) {
        const sum = components.reduce((total, v) => total + v.value!, 0);
        expect(region.value).toBeCloseTo(sum, 6);
        expect(region.status).toBe("derived_sum");
      } else if (available.length) {
        expect(region.value).toBeCloseTo(available.reduce((total, v) => total + v.value!, 0), 6);
        expect(region.status).toBe("partial_sum");
      } else {
        expect(region.value).toBeNull();
        expect(region.status).toBe(components.some((v) => v.status === "suppressed")
          ? "suppressed" : "incomplete_sum");
      }
    }
    await page.goto(`/dashboard?kpi=${sample.id}&nivel=regiao&periodo=${sample.period}`);
    await expect(page.locator('path[data-key="regiao:3"]')).toBeVisible();
    await expect(page.locator(".meta-more")).toContainText("Grandes Regiões derivadas");
    await expect(page.locator(".meta-more")).toContainText("parcial");
    if (regions.some((v) => v.status === "partial_sum")) {
      await expect(page.getByRole("note").filter({ hasText: "Valores parciais" })).toBeVisible();
      const partial = regions.find((v) => v.status === "partial_sum")!;
      await page.locator(`path[data-key="${partial.geography_key}"]`).focus();
      await expect(page.locator(".tooltip")).toContainText("(parcial)");
    }
    await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
    await page.screenshot({ path: `test-results/completude-${sample.id}.png` });
  });
}

test("casamentos mensais em todos os municípios e anos publicados", async ({ page, request }) => {
  const response = await request.get(
    "/odb-api/kpis/casamentos_mensal/map?level=municipio&period=2024M01",
  );
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  expect(data.values).toHaveLength(5570);
  expect(data.values.find((v: MapValue) => v.geography_key === "municipio:3550308").value)
    .toBe(3719);
  const metadata = await request.get("/odb-api/kpis/casamentos_mensal");
  const kpi = await metadata.json();
  expect(kpi.periods_by_level.municipio).toContain("2013M01");
  expect(kpi.periods_by_level.municipio).toContain("2024M12");
  expect(kpi.caveats.join(" ")).toContain("Meses de anos anteriores");
  await page.goto(
    "/dashboard?kpi=casamentos_mensal&nivel=municipio&periodo=2024M01&territorio=municipio:3550308&foco=uf:35",
  );
  await expect(page.getByRole("heading", { level: 1, name: "Casamentos por mês", exact: true }))
    .toBeVisible();
  await expect(page.locator('path[data-key="municipio:3550308"]')).toBeVisible();
  await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
  await page.screenshot({ path: "test-results/completude-casamentos-mensal.png" });
});

test("casamentos municipais preservam os detalhes anuais dos dois cônjuges", async ({ request }) => {
  for (const dimension of ["c664", "c665", "c666", "c667"]) {
    const response = await request.get(
      `/odb-api/kpis/casamentos/detail?geography=municipio:3550308&period=2024&dimensions=${dimension}`,
    );
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.root.value).toBe(54892);
    expect(data.root.children.length).toBeGreaterThan(0);
    if (dimension === "c664") {
      expect(data.root.children.find((c: { category_key: string }) =>
        c.category_key === "c664:32960").value).toBe(43015);
    }
    if (dimension === "c666") {
      expect(data.root.children.find((c: { category_key: string }) =>
        c.category_key === "c666:32969").value).toBe(535);
    }
  }
});

test("valor regional parcial acompanha série, filtros, grãos, acumulado e exportação", async ({ request }) => {
  const base = "/odb-api/kpis/leite_adquirido";
  const mapResponse = await request.get(`${base}/map?level=regiao&period=2026T2`);
  expect(mapResponse.ok()).toBeTruthy();
  const north = (await mapResponse.json()).values.find((v: MapValue) => v.geography_key === "regiao:1");
  expect(north.value).not.toBeNull();
  expect(north.status).toBe("partial_sum");

  const seriesResponse = await request.get(`${base}/series?geography=regiao:1`);
  expect(seriesResponse.ok()).toBeTruthy();
  const points: { period: string; value: number | null; status: string }[] =
    (await seriesResponse.json()).series[0].points;
  expect(points.find((p) => p.period === "2026T2")).toMatchObject({
    value: north.value, status: "partial_sum",
  });
  const annualResponse = await request.get(`${base}/map?level=regiao&period=2025&grain=ano`);
  expect(annualResponse.ok()).toBeTruthy();
  const annual = (await annualResponse.json()).values.find((v: MapValue) => v.geography_key === "regiao:1");
  const quarters = points.filter((p) => p.period.startsWith("2025T"));
  expect(quarters).toHaveLength(4);
  expect(annual.status).toBe("partial_sum");
  expect(annual.value).toBeCloseTo(quarters.reduce((sum, p) => sum + p.value!, 0), 6);

  const accumulatedResponse = await request.get(
    `${base}/map?level=regiao&periods=2026T1,2026T2&accumulate=true`,
  );
  expect(accumulatedResponse.ok()).toBeTruthy();
  const accumulated = (await accumulatedResponse.json()).values.find((v: MapValue) =>
    v.geography_key === "regiao:1");
  expect(accumulated.status).toBe("partial_sum");
  expect(accumulated.value).toBeCloseTo(north.value + points.find((p) => p.period === "2026T1")!.value!, 6);

  const metadata = await request.get(base);
  const dimension = (await metadata.json()).dimensions[0].classification_id;
  const detailResponse = await request.get(`${base}/detail?geography=regiao:1&period=2026T2&dimensions=${dimension}`);
  expect(detailResponse.ok()).toBeTruthy();
  const child = (await detailResponse.json()).root.children.find((c: { status: string }) =>
    c.status === "partial_sum");
  expect(child).toBeTruthy();
  const filteredResponse = await request.get(`${base}/map?level=regiao&period=2026T2&categories=${child.category_key}`);
  expect(filteredResponse.ok()).toBeTruthy();
  expect((await filteredResponse.json()).values.find((v: MapValue) => v.geography_key === "regiao:1"))
    .toMatchObject({ value: child.value, status: "partial_sum" });

  const exportResponse = await request.post("/odb-api/exports", { data: {
    kpi_id: "leite_adquirido", level: "regiao", periods: ["2026T2"], format: "json",
  } });
  expect(exportResponse.ok()).toBeTruthy();
  const exported = await exportResponse.json();
  expect(exported.rows.find((r: { geography_key: string }) => r.geography_key === "regiao:1"))
    .toMatchObject({ valor: north.value, status: "partial_sum" });
  expect(exported.metadata.legenda_status.partial_sum).toContain("parcial");
});

test("aviso de soma parcial permanece legível no mapa do celular", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard?kpi=leite_adquirido&nivel=regiao&periodo=2026T2");
  const note = page.getByRole("note").filter({ hasText: "Valores parciais" });
  await expect(note).toBeVisible();
  await note.evaluate((element) => element.scrollIntoView({ block: "center" }));
  const box = (await note.boundingBox())!;
  const map = (await page.locator(".map-panel").boundingBox())!;
  const bar = (await page.locator(".mobile-bar").boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(map.x);
  expect(box.x + box.width).toBeLessThanOrEqual(map.x + map.width);
  expect(box.y).toBeGreaterThanOrEqual(map.y);
  expect(box.y + box.height).toBeLessThanOrEqual(map.y + map.height);
  expect(box.y + box.height).toBeLessThanOrEqual(bar.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "test-results/completude-parciais-mobile.png" });
});
