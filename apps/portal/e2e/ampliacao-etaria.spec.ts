import { expect, test } from "@playwright/test";

// Valores de amostras oficiais preservadas na auditoria municipal de 2026-11-16.
for (const id of ["taxa_alfabetizacao_censo", "alfabetizacao_serie"]) {
  test(`alfabetização municipal recupera 2010: ${id}`, async ({ page, request }) => {
    const metadata = await request.get(`/odb-api/kpis/${id}`);
    expect(metadata.ok()).toBeTruthy();
    expect((await metadata.json()).periods_by_level.municipio).toEqual(["2010", "2022"]);
    const map = await request.get(`/odb-api/kpis/${id}/map?level=municipio&period=2010`);
    expect(map.ok()).toBeTruthy();
    const values = (await map.json()).values;
    expect(values.find((v: { geography_key: string }) => v.geography_key === "municipio:3550308")
      .value).toBe(96.82);
    await page.goto(
      `/dashboard?kpi=${id}&nivel=municipio&periodo=2010&territorio=municipio:3550308&foco=uf:35`,
    );
    await expect(page.locator('path[data-key="municipio:3550308"]')).toBeVisible();
    await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
    await page.screenshot({ path: `test-results/ampliacao-${id}-2010.png` });
  });
}

for (const sample of [
  { id: "indigenas_em_terras_indigenas", city: "1303809", state: "13", value: 3451 },
  { id: "residentes_em_terras_indigenas", city: "1303809", state: "13", value: 3462 },
  { id: "pessoas_quilombolas", city: "2930105", state: "29", value: 1106 },
  { id: "quilombolas_em_territorios", city: "2100204", state: "21", value: 669 },
  { id: "residentes_em_territorios_quilombolas", city: "2100204", state: "21", value: 697 },
]) {
  test(`faixas etárias municipais oficiais: ${sample.id}`, async ({ page, request }) => {
    for (const geography of [`municipio:${sample.city}`, `uf:${sample.state}`, "regiao:2"]) {
      const response = await request.get(
        `/odb-api/kpis/${sample.id}/detail?geography=${geography}&period=2022&dimensions=c287`,
      );
      expect(response.ok()).toBeTruthy();
      const root = (await response.json()).root;
      expect(root.children).toHaveLength(21);
      if (geography.startsWith("municipio:")) {
        expect(root.children.find((child: { category_key: string }) =>
          child.category_key === "c287:93070").value).toBe(sample.value);
      }
    }
    await page.goto(`/dashboard?kpi=${sample.id}&nivel=municipio&periodo=2022`
      + `&territorio=municipio:${sample.city}&foco=uf:${sample.state}&dim=c287&cat=c287:93070`);
    await expect(page.locator(`path[data-key="municipio:${sample.city}"]`)).toBeVisible();
    await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
    await page.screenshot({ path: `test-results/ampliacao-${sample.id}-idade.png` });
  });
}

test("marginais indígenas já carregadas ficam acessíveis no portal", async ({ page, request }) => {
  const metadata = await request.get("/odb-api/kpis/pessoas_indigenas");
  expect(metadata.ok()).toBeTruthy();
  const dimensions = (await metadata.json()).dimensions;
  expect(dimensions.map((d: { classification_id: string }) => d.classification_id))
    .toEqual(["c2", "c58", "c1", "c2661"]);
  const response = await request.get("/odb-api/kpis/pessoas_indigenas/detail"
    + "?geography=municipio:1303809&period=2022&dimensions=c58");
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).root.children).toHaveLength(18);
  await page.goto("/dashboard?kpi=pessoas_indigenas&nivel=municipio&periodo=2022"
    + "&territorio=municipio:1303809&foco=uf:13&dim=c58");
  await expect(page.getByRole("checkbox", { name: "Grupos de idade", exact: true })).toBeChecked();
  await expect(page.locator('path[data-key="municipio:1303809"]')).toBeVisible();
  await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
  await page.screenshot({ path: "test-results/ampliacao-indigenas-marginais.png" });
});
