import { describe, expect, it } from "vitest";

import { flattenDetail } from "./detail";
import { groupInstitutions } from "./sources";
import { formatBound, formatCompact, formatPeriod, formatShare, formatValue } from "./format";
import { rewindForD3 } from "./geo";
import { MISSING_COLOR, ZERO_COLOR, nextNice, niceCuts, quantileScale, snapNice } from "./scale";
import { indexTitle, unitShort } from "./format";
import { navFixture } from "./fixtures";
import { allKpis, canAccumulate, canCross, grainPeriods, periodQuery, readState, writeState } from "./state";
import { fitView, levelOf, nextLevel, previousLevel, validFocus, zoomDecision, zoomLadder } from "./zoom";
import type { GeoCollection, Kpi, Navigation } from "./types";

describe("format", () => {
  it("formata em pt-BR e nunca transforma ausência em zero", () => {
    expect(formatValue(14141626)).toBe("14.141.626");
    expect(formatValue(57.31)).toBe("57,31");
    expect(formatValue(null, "suppressed")).toBe("X (sigilo)");
    expect(formatValue(undefined, "absent")).toBe("sem dado");
    expect(formatValue(1203, "partial_sum")).toBe("1.203 (parcial)");
    expect(formatValue(0, "partial_sum")).toBe("0 (parcial)");
    expect(formatShare(48.26)).toBe("48,3%");
    expect(formatShare(null)).toBe("");
    expect(formatCompact(203080756)).toMatch(/203,1\s?mi/);
  });
});

describe("unidades (DS 2.3.6)", () => {
  it("abrevia a unidade para colunas e legenda", () => {
    expect(unitShort("%")).toBe("%");
    expect(unitShort("Reais")).toBe("R$");
    expect(unitShort("Milhões de Reais")).toBe("R$ milhões");
    expect(unitShort("Número-índice")).toBe("índice");
    expect(unitShort("Mil pessoas")).toBe("mil pessoas");
    expect(indexTitle("PMC - Número-índice (2022=100)")).toBe("Índice (2022 = 100)");
    expect(indexTitle("IPCA - Número-índice (base: dezembro de 1993 = 100)")).toBe("Índice (dezembro de 1993 = 100)");
    expect(indexTitle(null)).toBe("Índice");
  });
});

describe("quantileScale", () => {
  it("usa 7 grupos por quantis, com limites redondos e pontas abertas", () => {
    const values = Array.from({ length: 70 }, (_, i) => i + 1);
    const scale = quantileScale(values);
    expect(scale.breaks.map((b) => b.kind)).toEqual(["first", "middle", "middle", "middle", "middle", "middle", "last"]);
    expect(scale.breaks.map((b) => b.to).slice(0, 6)).toEqual([10, 20, 30, 40, 50, 60]);
    expect(scale.color(1)).toBe(scale.breaks[0]?.color);
    expect(scale.color(10)).toBe(scale.breaks[0]?.color); // "Até 10" inclui o 10
    expect(scale.color(11)).toBe(scale.breaks[1]?.color);
    expect(scale.color(70)).toBe(scale.breaks[6]?.color);
    expect(scale.color(null)).toBe(MISSING_COLOR);
  });

  it("arredonda cortes como os do PDF da revisão (1.318 – 3.643 → Até 4 mil)", () => {
    // Quantis brutos 3.643 · 4.440 · 5.380 · 6.475 · 9.835 · 17.500 (municípios de uma UF).
    expect(snapNice(3643, true)).toBe(4000);
    expect(snapNice(4440, true)).toBe(4000); // repetiria o corte anterior…
    expect(nextNice(4000, true)).toBe(5000); // …então sobe para o próximo redondo
    expect(snapNice(9835, true)).toBe(10000);
    const ranked = [1318, 2000, 3000, 3643, 4100, 4440, 5000, 5380, 5900, 6475, 8000, 9835, 12000, 17500, 40000, 866300];
    const nice = niceCuts(ranked, 7, true);
    expect(nice.every((c, i) => i === 0 || c > (nice[i - 1] as number))).toBe(true);
    // Redondos: no máximo dois algarismos significativos (4 mil, 25 mil, 3,5 mil).
    expect(nice.every((c) => Number(c.toPrecision(2)) === c)).toBe(true);
    const scale = quantileScale(ranked);
    expect(scale.breaks[0]).toMatchObject({ kind: "first", to: nice[0] });
    expect(scale.breaks.at(-1)).toMatchObject({ kind: "last", from: nice.at(-1), to: 866300 });
    expect([formatBound(4000), formatBound(17500), formatBound(250), formatBound(0.25)]).toEqual(["4\u00a0mil", "17,5\u00a0mil", "250", "0,25"]);
  });

  it("não colapsa dados concentrados (esperança de vida, 7362, DS 2.3.6)", () => {
    // UFs de uma região: 72,8 a 77,6 anos. Antes: "Até 80" num grupo só.
    const life = [72.8, 73.1, 73.4, 74.0, 74.6, 75.2, 75.9, 76.7, 77.6];
    const scale = quantileScale(life);
    expect(scale.breaks.length).toBeGreaterThanOrEqual(5);
    const cuts = scale.breaks.slice(0, -1).map((b) => b.to);
    expect(cuts.every((c) => c > 72.8 && c < 77.6)).toBe(true);
    expect(cuts.every((c) => Number(c.toPrecision(3)) === c)).toBe(true);
    // Brasil inteiro (27 UFs de 71 a 80): vários grupos, não só "Até 80 · Mais de 80".
    const brazil = Array.from({ length: 27 }, (_, i) => 71 + (i * 9) / 26);
    expect(quantileScale(brazil).breaks.length).toBeGreaterThanOrEqual(6);
  });

  it("não cria grupos vazios e respeita inteiros e decimais", () => {
    expect(niceCuts([1, 1, 1, 2], 7, true)).toEqual([1]);
    expect(snapNice(0.237)).toBe(0.25);
    expect(snapNice(3.2, true)).toBe(3);
    expect(nextNice(0.25)).toBe(0.3);
    const single = quantileScale([5, 5, 5]);
    expect(single.breaks).toEqual([expect.objectContaining({ kind: "single", from: 5, to: 5 })]);
  });

  it("separa o zero quando é comum", () => {
    const values = [...Array(80).fill(0), 1, 2, 3, 5, 8, 13, 21, 34, 55, 89];
    const scale = quantileScale(values);
    expect(scale.breaks[0]).toEqual({ kind: "zero", from: 0, to: 0, color: ZERO_COLOR });
    expect(scale.color(0)).toBe(ZERO_COLOR);
    const ranges = scale.breaks.slice(1);
    expect(ranges.every((b) => b.from <= b.to)).toBe(true);
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
      full_label: "Total",
      classification_id: null,
      category_key: null,
      value: 100,
      status: "valid",
      share_pct: null,
      children: [
        {
          label: "Parda",
          full_label: "Parda",
          classification_id: "c86",
          category_key: "c86:2779",
          value: 60,
          status: "valid",
          share_pct: 60,
          children: [
            { label: "Homens", full_label: "Homens", classification_id: "c2", category_key: "c2:4", value: null, status: "suppressed", share_pct: null, children: [] },
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
  const kpi = (id: string, dims: string[], levels: string[], periods: string[], time_grains: Kpi["time_grains"] = []) => ({
    kpi_id: id,
    label: id,
    theme_id: "t",
    subtheme_id: "s",
    indicator_id: id,
    name: id,
    description: "",
    unit: "Pessoas",
    additivity: "additive",
    category_shares: true,
    periods,
    levels,
    map_levels: levels.filter((l) => l !== "terra_indigena"),
    dimensions: dims.map((d) => ({ classification_id: d, label: d, full_label: d, partition_id: d, total_category_key: `${d}:0`, categories: [], levels: [] as string[], source_table_ids: [] as string[] })),
    exclusive_dimensions: false,
    crossed: [],
    crossed_levels: [],
    corrections: [],
    caveats: [],
    time_grains,
    source: { dataset_id: "d", source_table_id: "1", source_variable_id: "1", source_variable_name: null, reference_url: null, license_id: null, tables: [] },
  });
  // Fluxo mensal (ADR-0013): jan 2025 a set 2026; 2026 e o 4º tri de 2026 incompletos.
  const months = [...Array.from({ length: 12 }, (_, i) => `2025M${String(i + 1).padStart(2, "0")}`), ...Array.from({ length: 9 }, (_, i) => `2026M${String(i + 1).padStart(2, "0")}`)];
  const flow = kpi("vit", [], ["brasil", "uf"], months, [
    { grain: "mes", label: "Mês", periods: months, complete_periods: months },
    { grain: "trimestre", label: "Trimestre", periods: ["2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2", "2026T3"], complete_periods: ["2025T1", "2025T2", "2025T3", "2025T4", "2026T1", "2026T2", "2026T3"] },
    { grain: "ano", label: "Ano", periods: ["2025", "2026"], complete_periods: ["2025"] },
  ]);
  const nav: Navigation = {
    release_id: "r",
    scope: "demografia",
    dimension_order: ["c86", "c2"],
    themes: [
      {
        theme_id: "t",
        label: "T",
        filters: [],
        subthemes: [
          {
            subtheme_id: "s",
            label: "S",
            planned: [],
            kpis: [kpi("pop", ["c86", "c2"], ["brasil", "uf", "municipio"], ["2010", "2022"]), kpi("ti", ["c2"], ["uf", "terra_indigena"], ["2022"]), flow],
          },
        ],
      },
    ],
  };

  it("lê a URL validando KPI, nível, período, dimensões e território", () => {
    const s = readState(new URLSearchParams("kpi=pop&nivel=municipio&periodo=2010&dim=c2,c86,c99&territorio=uf:29"), nav);
    expect(s).toEqual({ kpi: "pop", level: "municipio", grain: null, correction: null, period: "2010", periods: ["2010"], accumulate: false, dimensions: ["c86", "c2"], categories: [], geography: "uf:29", focus: null, isolate: false });
    const bad = readState(new URLSearchParams("kpi=x&nivel=zzz&periodo=1999&territorio=uf;drop"), nav);
    expect(bad).toEqual({ kpi: "pop", level: "uf", grain: null, correction: null, period: null, dimensions: [], categories: [], geography: "brasil:1", focus: null, isolate: false, periods: [], accumulate: false });
  });

  it("sem nível Brasil, abre no Total das áreas e nas regiões metropolitanas (ADR-0016)", () => {
    const old = kpi("pof", ["c201"], ["municipio", "regiao_metropolitana", "areas_pof"], ["1987", "1995"]);
    const pof: Navigation = {
      ...nav,
      themes: [{ theme_id: "t", label: "T", filters: [], subthemes: [{ subtheme_id: "s", label: "S", planned: [], kpis: [{ ...old, map_levels: [] }] }] }],
    };
    const s = readState(new URLSearchParams("kpi=pof&territorio=brasil:1"), pof);
    expect(s.geography).toBe("areas_pof:1");
    expect(s.level).toBe("regiao_metropolitana");
    expect(readState(new URLSearchParams("kpi=pof&territorio=regiao_metropolitana:1501"), pof).geography).toBe("regiao_metropolitana:1501");
  });

  it("com dimensões marginais, fica uma só (ADR-0016)", () => {
    const marginal = { ...kpi("pop", ["c86", "c2"], ["brasil", "uf"], ["2022"]), exclusive_dimensions: true };
    const one: Navigation = {
      ...nav,
      themes: [{ theme_id: "t", label: "T", filters: [], subthemes: [{ subtheme_id: "s", label: "S", planned: [], kpis: [marginal] }] }],
    };
    expect(readState(new URLSearchParams("kpi=pop&dim=c2,c86"), one).dimensions).toEqual(["c86"]);
  });

  it("lê o grão de tempo e valida o período nele (ADR-0013)", () => {
    const yearly = readState(new URLSearchParams("kpi=vit&grao=ano&periodo=2025"), nav);
    expect([yearly.grain, yearly.period]).toEqual(["ano", "2025"]);
    // Mês de um ano pedido no grão anual: descartado. O grão publicado não vai na URL.
    expect(readState(new URLSearchParams("kpi=vit&grao=ano&periodo=2025M03"), nav).period).toBeNull();
    expect(readState(new URLSearchParams("kpi=vit&grao=mes"), nav).grain).toBeNull();
    // Grão que o KPI não oferece (estoque ou sem o semestre): descartado.
    expect(readState(new URLSearchParams("kpi=vit&grao=semestre"), nav).grain).toBeNull();
    expect(readState(new URLSearchParams("kpi=pop&grao=ano"), nav).grain).toBeNull();
    expect(writeState({ ...yearly, period: null })).toBe("kpi=vit&nivel=uf&grao=ano");
  });

  it("sem período, o padrão do grão é o último completo", () => {
    const { periods, complete } = grainPeriods(flow as Kpi, "ano");
    expect(periods).toEqual(["2025", "2026"]);
    expect(complete.at(-1)).toBe("2025");
    expect(grainPeriods(flow as Kpi, null).periods.at(-1)).toBe("2026M09");
  });

  it("filtra os anos pelo nível e descarta o ano de outro nível ao trocar o mapa", () => {
    const pof = {
      ...kpi("pof", [], ["brasil", "uf", "municipio"], ["2002", "2008", "2018"]),
      periods_by_level: { brasil: ["2002", "2008", "2018"], municipio: ["2008"] },
    };
    const local: Navigation = {
      ...nav,
      themes: [{ theme_id: "t", label: "T", filters: [], subthemes: [
        { subtheme_id: "s", label: "S", planned: [], kpis: [pof] },
      ] }],
    };
    expect(grainPeriods(pof, null, "municipio").periods).toEqual(["2008"]);
    expect(grainPeriods(pof, null, "brasil").periods.at(-1)).toBe("2018");
    expect(readState(new URLSearchParams("kpi=pof&nivel=municipio&periodo=2018"), local).period).toBeNull();
  });

  it("não considera completo o ano com meses ausentes no nível escolhido", () => {
    const partial = { ...flow, periods_by_level: { municipio: months.slice(0, 6) } };
    expect(grainPeriods(partial, "ano", "municipio")).toEqual({ periods: ["2025"], complete: [] });
    expect(grainPeriods(partial, "trimestre", "municipio")).toEqual({
      periods: ["2025T1", "2025T2"], complete: ["2025T1", "2025T2"],
    });
  });

  it("abre na Grande Região quando o KPI tem esse mapa", () => {
    const withRegion: Navigation = {
      ...nav,
      themes: [{ theme_id: "t", label: "T", filters: [], subthemes: [{ subtheme_id: "s", label: "S", planned: [], kpis: [kpi("r", [], ["brasil", "regiao", "uf"], ["2022"])] }] }],
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

  it("filtro do Detalhar por (DS 2.4): só categorias das dimensões ativas, sem seleção completa", async () => {
    const { normalizeCategories } = await import("./state");
    const kpi = {
      dimensions: [
        { classification_id: "c79", categories: [{ category_key: "c79:1" }, { category_key: "c79:2" }, { category_key: "c79:3" }] },
        { classification_id: "c2", categories: [{ category_key: "c2:4" }, { category_key: "c2:5" }] },
      ],
    } as unknown as Parameters<typeof normalizeCategories>[0];
    expect(normalizeCategories(kpi, ["c79"], ["c79:1", "c79:3", "c2:4"])).toEqual(["c79:1", "c79:3"]);
    expect(normalizeCategories(kpi, ["c79"], ["c79:1", "c79:2", "c79:3"])).toEqual([]); // todas = sem filtro
    expect(normalizeCategories(kpi, [], ["c79:1"])).toEqual([]); // dimensão desligada
    expect(writeState({ kpi: "ti", level: "uf", grain: null, correction: null, period: null, dimensions: ["c79"], categories: ["c79:1"], geography: "brasil:1", focus: null, isolate: false, periods: [], accumulate: false })).toBe(
      "kpi=ti&nivel=uf&dim=c79&cat=c79%3A1",
    );
  });

  it("escreve só o que difere do padrão", () => {
    expect(writeState({ kpi: "ti", level: "uf", grain: null, correction: null, period: null, dimensions: ["c2"], categories: [], geography: "brasil:1", focus: null, isolate: false, periods: [], accumulate: false })).toBe(
      "kpi=ti&nivel=uf&dim=c2",
    );
    expect(writeState({ kpi: "pop", level: "municipio", grain: null, correction: null, period: null, dimensions: [], categories: [], geography: "brasil:1", focus: "uf:13", isolate: false, periods: [], accumulate: false })).toBe(
      "kpi=pop&nivel=municipio&foco=uf%3A13",
    );
  });

  it("detalhe só em alguns níveis (nota da tabela) continua pedido nos demais (DS 2.9: aviso no botão i)", () => {
    const diab = kpi("diabetes", ["c86", "c2"], ["brasil", "uf"], ["2019"]);
    diab.dimensions[1] = { ...diab.dimensions[1]!, levels: ["brasil"] };
    const t0 = nav.themes[0]!;
    const only: Navigation = { ...nav, themes: [{ ...t0, subthemes: [{ ...t0.subthemes[0]!, kpis: [diab as Kpi] }] }] };
    expect(readState(new URLSearchParams("kpi=diabetes&nivel=uf&dim=c2"), only).dimensions).toEqual(["c2"]);
    expect(readState(new URLSearchParams("kpi=diabetes&nivel=brasil&dim=c2"), only).dimensions).toEqual(["c2"]);
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

describe("formatPeriod", () => {
  it("formata ano, mês e trimestre da Gold", () => {
    expect(formatPeriod("2022")).toBe("2022");
    expect(formatPeriod("2026M09")).toBe("set 2026");
    expect(formatPeriod("2026M01")).toBe("jan 2026");
    expect(formatPeriod("2026T2")).toBe("T2 2026");
    expect(formatPeriod("2026S1")).toBe("S1 2026");
    expect(formatPeriod("2026M13")).toBe("2026M13");
  });
});

describe("canCross (C1)", () => {
  const kpi = { crossed: [["c2", "c260"]], crossed_levels: ["brasil", "regiao", "uf"] };
  it("cruza só no grupo e nos níveis declarados", () => {
    expect(canCross(kpi, ["c2", "c260"], "uf")).toBe(true);
    expect(canCross(kpi, ["c2", "c260"], "municipio")).toBe(false);
    expect(canCross(kpi, ["c2", "c244"], "uf")).toBe(false);
    expect(canCross(kpi, ["c2"], "municipio")).toBe(true);
    expect(canCross({}, ["c2", "c260"], "uf")).toBe(false);
  });
});

describe("período parcial", () => {
  it("marca o valor acumulado do período em andamento", () => {
    expect(formatValue(1203, "partial_period")).toBe("1.203 (parcial)");
    expect(formatValue(1203, "derived_sum")).toBe("1.203");
  });
});

describe("ícones de agropecuária (DS 2.3.14)", () => {
  it("mapeia grupos de lavoura, produtos do LSPA, rebanhos e produtos de origem animal", async () => {
    const { categoryIcon } = await import("@/components/agroIconMap");
    const { AGRO_ICONS } = await import("@/components/agroIcons");
    expect(categoryIcon("c782g:g_frutas")).toBe("frutas");
    expect(categoryIcon("c782:40151")).toBeNull(); // produto: o ícone é o do grupo
    expect(categoryIcon("c48:39428")).toBe("graos");
    expect(categoryIcon("c79:32794")).toBe("suino");
    expect(categoryIcon("c80:2687")).toBe("mel");
    for (const name of ["graos", "frutas", "suino", "leite", "mel"]) expect(AGRO_ICONS[name]).toBeTruthy();
  });
});


describe("groupInstitutions", () => {
  const src = (source_id: string, institution_id: string, acronym: string) => ({
    source_id,
    institution_id,
    institution_name: `Instituição ${acronym}`,
    institution_acronym: acronym,
    institution_url: `https://${acronym.toLowerCase()}.gov.br`,
    name: `Fonte ${source_id}`,
    connector_type: "http_file",
    base_url: `https://${source_id}.gov.br`,
    documentation_url: null,
  });
  const ds = (source_id: string) => ({ source_id }) as unknown as import("./types").Dataset;

  it("agrupa por instituição, conta conjuntos e omite fontes sem dados", () => {
    const out = groupInstitutions(
      [src("a-1", "a", "A"), src("a-2", "a", "A"), src("b-1", "b", "B"), src("c-1", "c", "C")],
      [ds("b-1"), ds("b-1"), ds("b-1"), ds("a-1"), ds("a-2"), ds("a-2")],
    );
    // Empate em 3 conjuntos: desempata pelo nome.
    expect(out.map((i) => [i.acronym, i.datasets])).toEqual([
      ["A", 3],
      ["B", 3],
    ]);
    expect(out.find((i) => i.id === "a")?.sources.map((s) => s.id)).toEqual(["a-2", "a-1"]);
    expect(out.some((i) => i.id === "c")).toBe(false);
    expect(out[0]?.sources[0]?.url).toMatch(/^https:/);
  });
});

describe("periodQuery (ADR-0026)", () => {
  const months = ["2024M11", "2024M12", "2025M01", "2025M02"];
  const flow = {
    ...allKpis(navFixture)[0]!,
    periods: months,
    time_aggregation: "sum",
    time_grains: [
      { grain: "mes", label: "Mês", periods: months, complete_periods: months },
      { grain: "trimestre", label: "Trimestre", periods: ["2024T4", "2025T1"], complete_periods: [] },
      { grain: "ano", label: "Ano", periods: ["2024", "2025"], complete_periods: [] },
    ],
  } as Kpi;
  const base = {
    kpi: flow.kpi_id, level: "uf", grain: null, correction: null, period: null, periods: [] as string[],
    accumulate: false, dimensions: [], categories: [], geography: "brasil:1", focus: null, isolate: false,
  };

  it("um período: consultas de sempre", () => {
    const q = periodQuery(flow, { ...base, period: "2025M01", periods: ["2025M01"] });
    expect(q.map).toEqual({ period: "2025M01", grain: null, periods: [], accumulate: false });
    expect(q.table.periods).toEqual([]);
  });

  it("vários períodos: tabela por coluna, mapa no último; Acumular soma tudo", () => {
    const sel = { ...base, period: "2025M02", periods: ["2024M12", "2025M01", "2025M02"] };
    const q = periodQuery(flow, sel);
    expect(q.map.period).toBe("2025M02");
    expect(q.table).toMatchObject({ periods: sel.periods, accumulate: null });
    const acc = periodQuery(flow, { ...sel, accumulate: true });
    expect(acc.map).toEqual({ period: null, grain: null, periods: sel.periods, accumulate: true });
    expect(acc.table.accumulate).toBe("total");
    expect(acc.series).toEqual({ periods: sel.periods, accumulate: "running" });
  });

  it("Isolar: preserva parcelas e não usa o antigo acumulado no ano", () => {
    const iso = { ...base, grain: "trimestre", isolate: true, period: "2025", periods: ["2025"], accumulate: true };
    const q = periodQuery(flow, iso);
    expect(q.map).toEqual({ period: "2025", grain: "ano", periods: [], accumulate: false });
    expect(q.table).toMatchObject({ grain: "trimestre", periods: ["2025T1"], accumulate: null });
    expect(q.series).toEqual({ periods: ["2025"], accumulate: null });
  });

  it("lê e escreve vários períodos e o acumulado na URL", () => {
    const local: Navigation = {
      ...navFixture,
      themes: [{ theme_id: "t", label: "T", filters: [], subthemes: [{ subtheme_id: "s", label: "S", planned: [], kpis: [flow] }] }],
    };
    const s = readState(new URLSearchParams(`kpi=${flow.kpi_id}&periodo=2025M01,2024M12,9999M01&acumular=1`), local);
    expect(s.periods).toEqual(["2024M12", "2025M01"]);
    expect(s.period).toBe("2025M01");
    expect(s.accumulate).toBe(true);
    expect(writeState(s)).toContain("periodo=2024M12%2C2025M01");
    expect(writeState(s)).toContain("acumular=1");
    expect(canAccumulate({ ...flow, time_aggregation: "mean" } as Kpi)).toBe(false);
  });
});
