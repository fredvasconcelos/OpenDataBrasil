import { expect, test } from "@playwright/test";

// Valores conferidos na API SIDRA: 7060/63 (outubro de 2026) e
// 4093/12466 (2º trimestre de 2026). A cobertura é a da pesquisa.
for (const sample of [
  {
    id: "ipca", label: "IPCA", period: "2026M10", geography: "municipio:2111300",
    focus: "uf:21", value: 0.45, count: 6,
  },
  {
    id: "taxa_informalidade_trimestral", label: "Taxa de informalidade (trimestral)",
    period: "2026T2", geography: "municipio:3550308", focus: "uf:35", value: 31.7, count: 27,
  },
]) {
  test(`cobertura territorial comprovada: ${sample.label}`, async ({ page, request }) => {
    const all = await request.get(
      `/odb-api/kpis/${sample.id}/map?level=municipio&period=${sample.period}`,
    );
    expect(all.ok()).toBeTruthy();
    expect((await all.json()).values).toHaveLength(sample.count);
    const response = page.waitForResponse((r) => {
      const url = new URL(r.url());
      return url.pathname === `/odb-api/kpis/${sample.id}/map`
        && url.searchParams.get("level") === "municipio" && r.status() === 200;
    });
    const query = new URLSearchParams({
      kpi: sample.id, nivel: "municipio", periodo: sample.period,
      territorio: sample.geography, foco: sample.focus,
    });
    await page.goto(`/dashboard?${query}`);
    await expect(page.getByRole("heading", {
      level: 1, name: sample.label, exact: true,
    })).toBeVisible();
    const data = await (await response).json();
    expect(data.values.find((v: { geography_key: string }) =>
      v.geography_key === sample.geography)?.value).toBe(sample.value);
    const map = page.getByRole("img", {
      name: new RegExp(sample.label.replace(/[()]/g, "\\$&")),
    });
    await expect(map.locator(`path[data-key="${sample.geography}"]`)).toBeVisible();
    await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
    await page.screenshot({ path: `test-results/territorial-${sample.id}.png` });
  });
}

test("calendário da informalidade respeita o início da variável e mantém a anual", async ({ request }) => {
  const quarterly = await request.get("/odb-api/kpis/taxa_informalidade_trimestral");
  expect(quarterly.ok()).toBeTruthy();
  const data = await quarterly.json();
  expect(data.periods[0]).toBe("2015T4");
  expect(data.periods).not.toContain("2015T1");
  expect(data.periods_by_level.municipio[0]).toBe("2015T4");
  expect(data.source.source_variable_id).toBe("12466");
  const annual = await request.get("/odb-api/kpis/taxa_informalidade");
  expect(annual.ok()).toBeTruthy();
  const old = await annual.json();
  expect(old.source.source_table_id).toBe("4708");
  expect(old.periods.every((p: string) => /^\d{4}$/.test(p))).toBeTruthy();
});

test("IPCA mantém o Brasil e distingue região metropolitana de UF", async ({ request }) => {
  const response = await request.get("/odb-api/kpis/ipca");
  expect(response.ok()).toBeTruthy();
  const kpi = await response.json();
  expect(kpi.source.source_table_id).toBe("1737");
  expect(kpi.levels).toContain("regiao_metropolitana");
  expect(kpi.levels).not.toContain("uf");
  expect(kpi.levels).not.toContain("regiao");
  const areas = await request.get(
    "/odb-api/kpis/ipca/table?level=regiao_metropolitana&period=2026M10",
  );
  expect(areas.ok()).toBeTruthy();
  expect((await areas.json()).rows).toHaveLength(10);
});
