import { describe, expect, it } from "vitest";

import { flattenDetail } from "./detail";
import { formatCompact, formatShare, formatValue } from "./format";
import { rewindForD3 } from "./geo";
import { MISSING_COLOR, quantileScale, ZERO_COLOR } from "./scale";
import { readState, writeState } from "./state";
import { fitView, levelOf, nextLevel, previousLevel, validFocus, zoomDecision, zoomLadder } from "./zoom";
import type { GeoCollection, Navigation } from "./types";

describe("format", () => {
  it("formata em pt-BR e nunca transforma ausência em zero", () => {
    expect(formatValue(14141626)).toBe("14.141.626");
    expect(formatValue(57.31)).toBe("57,31");
    expect(formatValue(null, "suppressed")).toBe("X (sigilo)");
    expect(formatValue(undefined, "absent")).toBe("sem dado");
    expect(formatShare(48.26)).toBe("48,3%");
    expect(formatShare(null)).toBe("");
    expect(formatCompact(203080756)).toMatch(/203,1\s?mi/);
  });
});

describe("quantileScale", () => {
  it("usa 7 faixas com a mesma quantidade de territórios", () => {
    const values = Array.from({ length: 70 }, (_, i) => i + 1);
    const scale = quantileScale(values);
    expect(scale.breaks).toHaveLength(7);
    expect(scale.color(1)).toBe(scale.breaks[0]?.color);
    expect(scale.color(70)).toBe(scale.breaks[6]?.color);
    expect(scale.color(null)).toBe(MISSING_COLOR);
  });

  it("separa o zero e não repete limites", () => {
    const values = [...Array(80).fill(0), 1, 2, 3, 5, 8, 13, 21, 34, 55, 89];
    const scale = quantileScale(values);
    expect(scale.breaks[0]).toEqual({ from: 0, to: 0, color: ZERO_COLOR });
    expect(scale.color(0)).toBe(ZERO_COLOR);
    const ranges = scale.breaks.slice(1);
    expect(ranges.every((b) => b.from < b.to)).toBe(true);
    expect(scale.color(89)).toBe(ranges.at(-1)?.color);
    expect(ranges.every((b) => Number.isInteger(b.from) && Number.isInteger(b.to))).toBe(true);
  });

  it("sem valores, tudo é ausente", () => {
    expect(quantileScale([null, undefined]).breaks).toEqual([]);
  });
});

describe("flattenDetail", () => {
  it("achata a árvore do tooltip na ordem de exibição", () => {
    const rows = flattenDetail({
      label: "Total",
      classification_id: null,
      category_key: null,
      value: 100,
      status: "valid",
      share_pct: null,
      children: [
        {
          label: "Parda",
          classification_id: "c86",
          category_key: "c86:2779",
          value: 60,
          status: "valid",
          share_pct: 60,
          children: [
            { label: "Homens", classification_id: "c2", category_key: "c2:4", value: null, status: "suppressed", share_pct: null, children: [] },
          ],
        },
      ],
    });
    expect(rows.map((r) => [r.label, r.depth, r.value, r.share])).toEqual([
      ["Total", 0, 100, null],
      ["Parda", 1, 60, 60],
      ["Homens", 2, null, null],
    ]);
  });
});

describe("geo", () => {
  it("inverte o anel da RFC 7946 para o d3 e preserva a área pequena", () => {
    const ccw = [
      [-40, -10],
      [-39, -10],
      [-39, -9],
      [-40, -9],
      [-40, -10],
    ];
    const collection: GeoCollection = {
      type: "FeatureCollection",
      metadata: { release_id: "r", level: "uf", within: null },
      features: [{ type: "Feature", id: "uf:29", properties: { name: "Bahia", uf: "BA" }, geometry: { type: "Polygon", coordinates: [ccw] } }],
    };
    const out = rewindForD3(collection).features[0]?.geometry as GeoJSON.Polygon;
    expect(out.coordinates[0]).toEqual([...ccw].reverse());
    // Já no sentido do d3: não inverte de novo.
    const again = rewindForD3({ ...collection, features: [{ ...collection.features[0]!, geometry: out }] });
    expect((again.features[0]?.geometry as GeoJSON.Polygon).coordinates[0]).toEqual(out.coordinates[0]);
  });
});

describe("state", () => {
  const kpi = (id: string, dims: string[], levels: string[], periods: string[]) => ({
    kpi_id: id,
    label: id,
    theme_id: "t",
    subtheme_id: "s",
    indicator_id: id,
    name: id,
    description: "",
    unit: "Pessoas",
    additivity: "additive",
    periods,
    levels,
    map_levels: levels.filter((l) => l !== "terra_indigena"),
    dimensions: dims.map((d) => ({ classification_id: d, label: d, partition_id: d, total_category_key: `${d}:0`, categories: [] })),
    caveats: [],
    source: { dataset_id: "d", source_table_id: "1", source_variable_id: "1", source_variable_name: null, reference_url: null, license_id: null },
  });
  const nav: Navigation = {
    release_id: "r",
    scope: "demografia",
    dimension_order: ["c86", "c2"],
    themes: [
      {
        theme_id: "t",
        label: "T",
        subthemes: [
          {
            subtheme_id: "s",
            label: "S",
            kpis: [kpi("pop", ["c86", "c2"], ["brasil", "uf", "municipio"], ["2010", "2022"]), kpi("ti", ["c2"], ["uf", "terra_indigena"], ["2022"])],
          },
        ],
      },
    ],
  };

  it("lê a URL validando KPI, nível, período, dimensões e território", () => {
    const s = readState(new URLSearchParams("kpi=pop&nivel=municipio&periodo=2010&dim=c2,c86,c99&territorio=uf:29"), nav);
    expect(s).toEqual({ kpi: "pop", level: "municipio", period: "2010", dimensions: ["c86", "c2"], geography: "uf:29", focus: null });
    const bad = readState(new URLSearchParams("kpi=x&nivel=zzz&periodo=1999&territorio=uf;drop"), nav);
    expect(bad).toEqual({ kpi: "pop", level: "uf", period: null, dimensions: [], geography: "brasil:1", focus: null });
  });

  it("abre na Grande Região quando o KPI tem esse mapa", () => {
    const withRegion: Navigation = {
      ...nav,
      themes: [{ theme_id: "t", label: "T", subthemes: [{ subtheme_id: "s", label: "S", kpis: [kpi("r", [], ["brasil", "regiao", "uf"], ["2022"])] }] }],
    };
    expect(readState(new URLSearchParams(""), withRegion).level).toBe("regiao");
  });

  it("aceita o recorte só se ele for mais agregado que o nível exibido", () => {
    expect(readState(new URLSearchParams("kpi=pop&nivel=municipio&foco=uf:29"), nav).focus).toBe("uf:29");
    // Recorte no mesmo nível ou abaixo do exibido, ou fora da escada do mapa: descartado.
    expect(readState(new URLSearchParams("kpi=pop&nivel=uf&foco=uf:29"), nav).focus).toBeNull();
    expect(readState(new URLSearchParams("kpi=pop&nivel=municipio&foco=brasil:1"), nav).focus).toBeNull();
    expect(readState(new URLSearchParams("kpi=pop&nivel=municipio&foco=uf;29"), nav).focus).toBeNull();
  });

  it("escreve só o que difere do padrão", () => {
    expect(writeState({ kpi: "ti", level: "uf", period: null, dimensions: ["c2"], geography: "brasil:1", focus: null })).toBe(
      "kpi=ti&nivel=uf&dim=c2",
    );
    expect(writeState({ kpi: "pop", level: "municipio", period: null, dimensions: [], geography: "brasil:1", focus: "uf:13" })).toBe(
      "kpi=pop&nivel=municipio&foco=uf%3A13",
    );
  });
});

describe("zoom", () => {
  const ladder = zoomLadder(["brasil", "municipio", "uf", "regiao", "terra_indigena"]);

  it("monta a escada na ordem de aprofundamento, só com níveis que têm mapa", () => {
    expect(ladder).toEqual(["regiao", "uf", "municipio"]);
    expect(zoomLadder(["uf", "municipio"])).toEqual(["uf", "municipio"]);
  });

  it("decide o gesto pela escala relativa à do recorte atual", () => {
    // Aproximar 2× além do recorte abre o seguinte; afastar abaixo de 0,6× volta.
    expect(zoomDecision(2, 1, false)).toBe("drill");
    expect(zoomDecision(1.9, 1, false)).toBeNull();
    expect(zoomDecision(5, 2.5, true)).toBe("drill");
    expect(zoomDecision(1.4, 2.5, true)).toBe("up");
    expect(zoomDecision(1.6, 2.5, true)).toBeNull();
    // De volta à escala 1 com recorte aberto: Brasil inteiro.
    expect(zoomDecision(1, 1.5, true)).toBe("reset");
    // Sem nada acima, afastar não faz nada.
    expect(zoomDecision(1, 3, false)).toBeNull();
  });

  it("aprofunda e sobe um nível por vez", () => {
    expect(nextLevel(ladder, "regiao")).toBe("uf");
    expect(nextLevel(ladder, "uf")).toBe("municipio");
    expect(nextLevel(ladder, "municipio")).toBeNull();
    expect(nextLevel(ladder, "brasil")).toBe("regiao");
    expect(previousLevel(ladder, "uf")).toBe("regiao");
    expect(previousLevel(ladder, "regiao")).toBeNull();
    expect(levelOf("municipio:2927408")).toBe("municipio");
  });

  it("valida o recorte contra a escada e o nível exibido", () => {
    expect(validFocus(ladder, "regiao:1", "uf")).toBe(true);
    expect(validFocus(ladder, "regiao:1", "municipio")).toBe(true);
    expect(validFocus(ladder, "uf:13", "uf")).toBe(false);
    expect(validFocus(ladder, "brasil:1", "uf")).toBe(false);
    expect(validFocus(ladder, null, "uf")).toBe(false);
  });

  it("enquadra o território no centro da tela, com margem", () => {
    const view = fitView([[100, 100], [300, 200]], 800, 400);
    expect(view.k).toBeCloseTo(0.9 / Math.max(200 / 800, 100 / 400));
    expect(view.x + view.k * 200).toBeCloseTo(400);
    expect(view.y + view.k * 150).toBeCloseTo(200);
    // A escala respeita os limites pedidos.
    expect(fitView([[0, 0], [800, 400]], 800, 400, [1.5, 80]).k).toBe(1.5);
  });
});
