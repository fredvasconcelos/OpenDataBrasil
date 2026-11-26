"use client";

import { useTranslations } from "next-intl";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PivotControls, PivotTable } from "@/components/PivotTable";
import { DetailTooltip } from "@/components/DetailTooltip";
import { DataExport, MapImageExport } from "@/components/ExportMenu";
import { CollapseIcon, ExpandIcon, FilterIcon, ListIcon } from "@/components/icons";
import { KpiInfo } from "@/components/KpiInfo";
import { MapView, type FitRequest } from "@/components/MapView";
import { SeasonChart } from "@/components/SeasonChart";
import { SeasonalChart } from "@/components/SeasonalChart";
import { SeriesChart } from "@/components/SeriesChart";
import { Sidebar } from "@/components/Sidebar";
import { api, ApiRequestError } from "@/lib/api";
import { formatPeriod, formatValue, indexTitle, legendTitleKey, unitShort } from "@/lib/format";
import {
  resolveKpiId,
  defaultGeography,
  grainPeriods,
  normalizeCategories,
  periodQuery,
  readState,
  selectablePeriods,
  writeState,
  yearsOf,
  canAccumulate,
  timeGrains,
  type DashboardState,
} from "@/lib/state";
import type {
  Detail,
  GeoCollection,
  Geography,
  MapData,
  Kpi,
  PortalIndex,
} from "@/lib/types";
import { KpiCache } from "@/lib/kpiCache";
import { useAsync } from "@/lib/useAsync";
import { COARSE_QUERY, MOBILE_QUERY, useMediaQuery } from "@/lib/useMediaQuery";
import {
  levelOf,
  nextLevel,
  previousLevel,
  validFocus,
  zoomLadder,
} from "@/lib/zoom";

interface Hover {
  key: string;
  name: string;
  x: number;
  y: number;
}

function Failure({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const t = useTranslations("dashboard");
  return (
    <div role="alert" className="error">
      <span>
        {error instanceof ApiRequestError && error.status === 503 ? t("busy") : t("error")}
      </span>
      <button type="button" className="primary" onClick={onRetry}>
        {t("retry")}
      </button>
    </div>
  );
}

/**
 * Layout inicial da tabela (DS 2.18). Até dois detalhes ficam nas colunas, sob o Período.
 * Com três ou mais, o de mais categorias desce para as linhas, ao lado do Território:
 * Cor ou raça × Sexo × Idade nas colunas dava 6 × 3 × 22 = 396 colunas.
 */
export function defaultPivotLayout(
  dims: readonly string[],
  catalog: readonly { classification_id: string; categories?: readonly unknown[] }[],
): { rows: string[]; cols: string[] } {
  if (dims.length < 3) return { rows: ["territorio"], cols: ["periodo", ...dims] };
  const size = (id: string) => catalog.find((d) => d.classification_id === id)?.categories?.length ?? 0;
  const largest = dims.reduce((a, b) => (size(b) > size(a) ? b : a));
  return { rows: ["territorio", largest], cols: ["periodo", ...dims.filter((d) => d !== largest)].slice(0, 3) };
}

export function Dashboard({ index, initialKpi }: { index: PortalIndex; initialKpi: Kpi | null }) {
  const t = useTranslations("dashboard");
  const router = useRouter();
  const params = useSearchParams();
  const cache = useMemo(() => new KpiCache(index.release_id, initialKpi), [index.release_id, initialKpi]);
  const id = resolveKpiId(new URLSearchParams(params.toString()), index);
  const [retry, setRetry] = useState(0);
  const metadata = useAsync(id && id !== initialKpi?.kpi_id ? () => cache.get(id) : null, [id, index.release_id], retry);
  const kpi = id === initialKpi?.kpi_id ? initialKpi : metadata.data;
  if (metadata.error) return <div className="page"><Failure error={metadata.error} onRetry={() => {
    if (metadata.error instanceof ApiRequestError && metadata.error.status === 409) router.refresh();
    setRetry((n) => n + 1);
  }} /></div>;
  if (metadata.loading) return <p className="page" role="status">{t("loading")}</p>;
  if (!kpi) return <p className="page">{t("selectKpi")}</p>;
  return <LoadedDashboard key={kpi.kpi_id} nav={index} kpi={kpi} onPreload={(id) => cache.preload(id)} />;
}

function LoadedDashboard({ nav, kpi, onPreload }: { nav: PortalIndex; kpi: Kpi; onPreload: (id: string) => void }) {
  const t = useTranslations();
  const pathname = usePathname();
  const params = useSearchParams();
  const state = useMemo(
    () => readState(new URLSearchParams(params.toString()), nav, kpi),
    [params, nav, kpi],
  );
  const [retry, setRetry] = useState(0);
  const [hover, setHover] = useState<Hover | null>(null);
  // Versão mobile (DS v2.5, até 991 px desde o DS 2.18): barra lateral vira painel inferior ("sheet") e
  // mapa, série e tabela viram abas. No desktop esses estados não têm efeito visual.
  const mobile = useMediaQuery(MOBILE_QUERY);
  const coarse = useMediaQuery(COARSE_QUERY);
  const [sheet, setSheet] = useState<"filters" | "themes" | null>(null);
  const [view, setView] = useState<"map" | "chart" | "table">("map");
  // Tabela ampliada (DS 2.17): ocupa a janela por cima do painel; Esc ou o mesmo botão fecham.
  const [tableWide, setTableWide] = useState(false);
  const tableToggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!tableWide) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setTableWide(false);
      tableToggle.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    document.documentElement.classList.add("has-table-wide");
    return () => {
      window.removeEventListener("keydown", onKey);
      document.documentElement.classList.remove("has-table-wide");
    };
  }, [tableWide]);
  // Tabela dinâmica (B6; única tabela desde o DS 2.9): campos nas linhas e colunas, por
  // KPI e detalhes ativos. Mudar "Detalhar por" volta ao arranjo padrão.
  const [pivotFor, setPivotFor] = useState<{ key: string; rows: string[]; cols: string[] } | null>(null);
  const sheetClose = useRef<HTMLButtonElement>(null);
  // Painel inferior aberto: foco no botão de fechar, Esc fecha e a página atrás não rola.
  useEffect(() => {
    if (!mobile || sheet === null) return;
    sheetClose.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setSheet(null);
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [mobile, sheet]);
  const [details, setDetails] = useState<Record<string, Detail>>({});
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  // Enquadramentos pedidos ao mapa. Um recorte vindo da URL é enquadrado ao abrir.
  const [fit, setFit] = useState<FitRequest | null>(() =>
    state.focus ? { key: state.focus, n: 1 } : null,
  );
  const requestFit = (key: string | null) =>
    setFit((f) => ({ key, n: (f?.n ?? 0) + 1 }));

  const update = useCallback(
    (patch: Partial<DashboardState>) => {
      const next = { ...state, ...patch };
      // Nível, grão ou Isolar mudaram: a seleção de períodos fica só com o que existe
      // (ex.: um ano sem cobertura municipal sai; com Isolar, só anos).
      if (kpi && ("level" in patch || "grain" in patch || "isolate" in patch)) {
        const valid = selectablePeriods(kpi, next.grain, next.level, next.isolate);
        next.periods = next.periods.filter((p) => valid.includes(p));
        next.period = next.periods.at(-1) ?? (next.period && valid.includes(next.period) ? next.period : null);
      }
      // O Next sincroniza useSearchParams com a History API nativa. Alterar filtros
      // não precisa renderizar novamente o HTML nem baixar outro índice (Plano D, D1).
      window.history.replaceState(null, "", `${pathname}?${writeState(next)}`);
    },
    [state, pathname, kpi],
  );

  const hasMap = Boolean(kpi?.map_levels.includes(state.level));
  const kpiId = kpi?.kpi_id ?? null;
  const focus = state.focus;
  // Períodos das consultas (ADR-0026): seleção, Isolar e Acumular.
  const pq = periodQuery(kpi, state);
  const pqKey = JSON.stringify(pq);
  const focusLevel = focus ? levelOf(focus) : null;
  // Recorte: os territórios coloridos são os do nível exibido dentro dele; o nível do
  // próprio recorte, no país inteiro, vira o contexto em cinza.
  const geometry = useAsync(
    hasMap ? () => api.geometry(state.level, focus) : null,
    [state.level, focus, hasMap],
    retry,
  );
  const context = useAsync(
    hasMap && focusLevel ? () => api.geometry(focusLevel) : null,
    [focusLevel, hasMap],
    retry,
  );
  const values = useAsync(
    kpiId
      ? () =>
          api.map(kpiId, {
            level: state.level,
            period: pq.map.period,
            within: focus,
            grain: pq.map.grain,
            correction: state.correction,
            categories: state.categories,
            periods: pq.map.periods,
            accumulate: pq.map.accumulate,
          })
      : null,
    [kpiId, state.level, pqKey, focus, state.correction, state.categories.join()],
    retry,
  );
  // Trilha do recorte (ex.: Norte › Amazonas), pelos territórios pais publicados na Gold.
  const ladder = useMemo(() => zoomLadder(kpi?.map_levels ?? []), [kpi]);
  const trail = useAsync(
    focus
      ? async () => {
          const chain: Geography[] = [];
          let key: string | null = focus;
          while (key && (ladder.includes(levelOf(key)) || ["regiao", "uf"].includes(levelOf(key))) && chain.length < 4) {
            const g: Geography = await api.geography(key);
            chain.unshift(g);
            key = g.parent_key;
          }
          return chain;
        }
      : null,
    [focus, ladder.join()],
  );
  const states = useAsync(kpi.levels.includes("municipio") ? () => api.geographies("uf") : null, [nav.release_id, kpi.levels.includes("municipio")]);
  const batchParams = {
    period: pq.map.period, periods: pq.map.periods, accumulate: pq.map.accumulate,
    dimensions: state.dimensions, grain: pq.map.grain, correction: state.correction,
    categories: state.categories,
  };
  const batchAllowed = ["brasil", "regiao", "uf"].includes(state.level) || (state.level === "municipio" && focus?.startsWith("uf:"));
  const batch = useAsync(
    hasMap && batchAllowed ? () => api.details(kpi.kpi_id, { ...batchParams, level: state.level, within: focus }) : null,
    [kpiId, state.level, focus, pqKey, state.dimensions.join(), state.categories.join(), state.correction], retry,
  );
  const contextBatch = useAsync(
    hasMap && focusLevel && kpi.levels.includes(focusLevel) && ["regiao", "uf"].includes(focusLevel)
      ? () => api.details(kpi.kpi_id, { ...batchParams, level: focusLevel }) : null,
    [kpiId, focusLevel, pqKey, state.dimensions.join(), state.categories.join(), state.correction], retry,
  );
  const batchDetails = useMemo(() => new Map([...(batch.data ?? []), ...(contextBatch.data ?? [])].map((detail) => [detail.geography.geography_key, detail])), [batch.data, contextBatch.data]);
  const seasonalMode = state.isolate && state.accumulate;
  const seasonalYears = pq.series.periods;
  const seasonal = useAsync(seasonalMode && seasonalYears.length ? () => api.seasonal(kpiId, {
    geography: state.geography, dimensions: state.dimensions, categories: state.categories,
    grain: state.grain, correction: state.correction,
    year_from: Number(seasonalYears[0]), year_to: Number(seasonalYears.at(-1)),
  }) : null, [kpiId, state.geography, state.dimensions.join(), state.categories.join(), state.grain, state.correction, pqKey], retry);
  const series = useAsync(
    kpiId && !seasonalMode
      ? () =>
          api.series(kpiId, {
            geography: state.geography,
            dimensions: state.dimensions,
            grain: state.grain,
            correction: state.correction,
            categories: state.categories,
            periods: pq.series.periods,
            accumulate: pq.series.accumulate,
          })
      : null,
    [kpiId, state.geography, state.dimensions.join(), state.categories.join(), state.grain, state.correction, pqKey],
    retry,
  );
  // Detalhes ativos que existem no nível (os demais viram aviso no botão i da tabela).
  const levelDims = (kpi?.dimensions ?? []).filter((d) => !d.levels?.length || d.levels.includes(state.level));
  // O detalhe pedido segue para a API mesmo indisponível: ela emite V1/V2.
  const tableDims = state.dimensions;
  // Períodos da tabela: os escolhidos (ou as partes dos anos, com Isolar); sem escolha, o
  // padrão do mapa (o último completo). Nunca acumulada (ADR-0026).
  const tablePeriods = (() => {
    if (!kpi) return [];
    if (pq.table.periods.length) return pq.table.periods;
    if (pq.table.period) return [pq.table.period];
    const { periods, complete } = grainPeriods(kpi, state.grain, state.level);
    const last = complete.at(-1) ?? periods.at(-1);
    return last ? [last] : [];
  })();
  const pivotKey = `${kpiId}|${tableDims.join()}`;
  const pivotLayout =
    pivotFor?.key === pivotKey ? pivotFor : { key: pivotKey, ...defaultPivotLayout(tableDims, kpi?.dimensions ?? []) };
  const pivotControls = (
    <PivotControls
      fields={[
        { id: "territorio", label: t("table.territory") },
        { id: "periodo", label: t("table.period") },
        ...(kpi?.dimensions ?? []).filter((d) => levelDims.includes(d) || state.dimensions.includes(d.classification_id)).map((d) => ({ id: d.classification_id, label: d.label })),
      ]}
      rows={pivotLayout.rows}
      cols={pivotLayout.cols}
      onChange={(rows, cols) => setPivotFor({ key: pivotKey, rows, cols })}
    />
  );
  const pivot = useAsync(
    kpiId
      ? () =>
          api.pivot(kpiId, {
            level: state.level,
            within: focus,
            rows: pivotLayout.rows,
            cols: pivotLayout.cols,
            periods: tablePeriods,
            grain: pq.table.grain,
            correction: state.correction,
            categories: state.categories,
          })
      : null,
    [kpiId, state.level, focus, pivotLayout.rows.join(), pivotLayout.cols.join(), tablePeriods.join(), pq.table.grain, state.correction, state.categories.join()],
    retry,
  );

  // O mapa continua montado enquanto o próximo nível carrega (o zoom não se perde):
  // mostra o último par geometria + valores coerente até o novo chegar.
  const fresh =
    geometry.data &&
    values.data &&
    (!focus || context.data) &&
    geometry.data.metadata.level === values.data.level &&
    values.data.kpi_id === kpiId
      ? {
          geometry: geometry.data,
          context: focus ? context.data : null,
          values: values.data,
        }
      : null;
  const [shown, setShown] = useState<{
    geometry: GeoCollection;
    context: GeoCollection | null;
    values: MapData;
  } | null>(null);
  if (
    fresh &&
    (fresh.geometry !== shown?.geometry ||
      fresh.context !== shown?.context ||
      fresh.values !== shown?.values)
  )
    setShown(fresh);
  // Territórios desenhados agora: o tooltip só aparece para eles (o ponteiro parado
  // durante o zoom pode ter ficado sobre um território que saiu do mapa).
  const drawn = useMemo(
    () =>
      new Set(
        [
          ...(shown?.geometry.features ?? []),
          ...(shown?.context?.features ?? []),
        ]
          .map((f) => f.id)
          .filter((id) => id !== focus),
      ),
    [shown, focus],
  );

  // Ampliação seletiva: abrir o recorte num território, subir um recorte, voltar ao Brasil.
  const drill = (key: string, source: "click" | "gesture"): boolean => {
    const next = ladder.includes(levelOf(key))
      ? nextLevel(ladder, levelOf(key))
      : null;
    if (!next) return false;
    update({
      focus: key,
      level: next,
      geography: source === "click" ? key : state.geography,
    });
    if (source === "click") requestFit(key);
    return true;
  };
  const up = () => {
    if (focus) {
      const chain = trail.data ?? [];
      const at = chain.findIndex((g) => g.geography_key === focus);
      const parent = at > 0 ? (chain[at - 1]?.geography_key ?? null) : null;
      const level = parent ? nextLevel(ladder, levelOf(parent)) : null;
      update(
        parent && level
          ? { focus: parent, level }
          : { focus: null, level: ladder[0] ?? state.level },
      );
    } else {
      const previous = previousLevel(ladder, state.level);
      if (previous) update({ level: previous });
    }
  };
  const reset = () => update({ focus: null, level: ladder[0] ?? state.level });
  const canUp = Boolean(focus) || previousLevel(ladder, state.level) !== null;

  const detailKey = (geo: string) =>
    `${kpiId}|${state.correction ?? ""}|${JSON.stringify(pq.map)}|${state.dimensions.join()}|${state.categories.join()}|${geo}`;
  const onHover = (
    key: string | null,
    name: string,
    e: { clientX: number; clientY: number },
  ) => {
    if (pending.current) clearTimeout(pending.current);
    if (!key || !kpiId) {
      setHover(null);
      return;
    }
    if (!drawn.has(key)) return;
    if (!kpi.levels.includes(levelOf(key))) {
      setHover(null);
      return;
    }
    setHover({ key, name, x: e.clientX, y: e.clientY });
    const level = levelOf(key);
    if ((level === state.level && batchAllowed) || ["regiao", "uf"].includes(level)) return;
    const cacheKey = detailKey(key);
    if (details[cacheKey]) return;
    pending.current = setTimeout(() => {
      api
        .detail(kpiId, {
          geography: key,
          period: pq.map.period,
          periods: pq.map.periods,
          accumulate: pq.map.accumulate,
          dimensions: state.dimensions,
          grain: pq.map.grain,
          correction: state.correction,
          categories: state.categories,
        })
        .then((d) => setDetails((all) => ({ ...all, [cacheKey]: d })))
        .catch(() => undefined);
    }, 120);
  };

  if (!kpi) return <p className="page">{t("dashboard.selectKpi")}</p>;
  // Sem período escolhido: o último completo do grão (ex.: o último ano com 12 meses).
  const { periods: grainList, complete } = grainPeriods(kpi, state.grain, state.level);
  const period = state.period ?? complete.at(-1) ?? grainList.at(-1) ?? "";
  // Seleção mostrada no filtro: a escolhida ou, sem escolha, o padrão (com Isolar, o ano dele).
  const selection = pq.selection.length ? pq.selection : state.isolate ? yearsOf([period]) : [period];
  const first = selection[0] ?? period;
  const last = selection.at(-1) ?? period;
  const range = first === last ? formatPeriod(last) : t("dashboard.periodRange", { from: formatPeriod(first), to: formatPeriod(last) });
  const periodLabel = seasonalMode || (state.isolate && !timeGrains(kpi).some((g) => g.grain === "ano"))
    ? formatPeriod(pq.map.period ?? period)
    : state.isolate
    ? `${selection.map(formatPeriod).join(", ")}${state.accumulate ? ` (${t("dashboard.accumulated")})` : ""}`
    : state.accumulate
      ? `${range} (${t("dashboard.accumulated")})`
      : selection.length > 1
        ? range
        : formatPeriod(period);
  const levelLabel = t(`levels.${state.level}`);
  // Tabela: os períodos dela, sem acumular (ADR-0026).
  const tableLabel = selection.length > 1 || state.isolate ? range : formatPeriod(period);
  const crumb =
    nav.themes
      .flatMap((th) =>
        th.subthemes
          .filter((s) => s.kpis.some((k) => k.kpi_id === kpi.kpi_id))
          .map((s) => `${th.label} › ${s.label}`),
      )
      .at(0) ?? "";
  // Território inicial do KPI: o Brasil ou, sem ele, o "Total das áreas" da POF antiga.
  const home = defaultGeography(kpi);
  const selectedName =
    state.geography === home
      ? t(`levels.${home.split(":")[0]}`)
      : (values.data?.values.find((v) => v.geography_key === state.geography)
          ?.name ??
        shown?.context?.features.find((f) => f.id === state.geography)
          ?.properties.name ??
        seasonal.data?.geography.name ??
        series.data?.geography.name ??
        state.geography);
  const defaults = readState(new URLSearchParams({ kpi: kpi.kpi_id }), nav, kpi);
  const filtered = writeState(state) !== writeState(defaults);
  const clear = () => {
    update(defaults);
    requestFit(null);
  };
  // Clique no mapa: seleciona o território; a tabela rola até a linha dele.
  const selectOnMap = (key: string) => update({ geography: key });
  const focusName = focus ? (trail.data?.at(-1)?.name ?? null) : null;
  const scope = `${levelLabel}${focusName ? ` · ${focusName}` : ""}`;
  const sourceRef =
    kpi.source.system === "SIDRA" || !kpi.source.institution
      ? `tabela ${kpi.source.source_table_id}`
      : kpi.source.source_table_id;
  const caption = `${kpi.label} · ${scope} · ${periodLabel} · Fonte: ${kpi.source.institution ?? "IBGE"}, ${sourceRef} · release ${nav.release_id}`;
  // Quantos filtros estão ativos, para o botão "Filtros (n)" da barra inferior.
  const activeFilters =
    state.dimensions.length +
    (state.period || state.periods.length ? 1 : 0) +
    (state.accumulate ? 1 : 0) +
    (state.grain ? 1 : 0) +
    (state.correction ? 1 : 0) +
    (state.isolate ? 1 : 0) +
    (state.level !== defaults.level ? 1 : 0);
  const selectedValue =
    state.geography !== home ? values.data?.values.find((v) => v.geography_key === state.geography) : undefined;
  const legendKey = legendTitleKey(kpi.unit);
  // KPIs cujo Total é só o universo: o mapa mostra o % de uma categoria (map_share).
  // Correção por índice de preços (ADR-0020): "R$ de jan/2018 · IPCA geral".
  const priced = values.data?.provenance.correction
    ? ` · ${values.data.provenance.correction_label}, preços de ${values.data.provenance.price_base}`
    : "";
  const legendTitle =
    values.data?.measure === "share" && values.data.measure_label
      ? values.data.measure_label
      : legendKey
        ? t(`dashboard.legend.title.${legendKey}`)
        : kpi.unit === "Número-índice"
          ? indexTitle(kpi.source.source_variable_name)
          : unitShort(kpi.unit) === kpi.unit.toLowerCase()
            ? kpi.unit
            : `${kpi.unit} (${unitShort(kpi.unit)})`;

  // Painel (Design System ODBr v2): filtros na barra lateral; exportações junto do
  // que exportam (imagem → cabeçalho do mapa; dados → "Gráfico e tabela"). Layout
  // por CSS (.dash-grid): empilhado até 1599 px; tela cheia sem rolagem a partir de
  // 1600 px (mapa à esquerda, gráfico e tabela à direita, fonte no rodapé).
  const chartHeading = (
    <h2 id="series-title">
      {t("dashboard.seriesTitle")} · {selectedName}
      {state.accumulate ? ` (${t("dashboard.accumulated")})` : ""}{" "}
      {state.geography !== home ? (
        <button
          type="button"
          className="small"
          onClick={() => update({ geography: home })}
        >
          {t("dashboard.resetSelection")}
        </button>
      ) : null}
    </h2>
  );
  const sheetOpen = mobile && sheet !== null;
  return (
    <div className="dashboard">
      {sheetOpen ? <button type="button" className="sheet-backdrop" tabIndex={-1} aria-label={t("dashboard.mobile.close")} onClick={() => setSheet(null)} /> : null}
      <div
        className="sheet-host"
        data-sheet={sheet ?? "closed"}
        role={sheetOpen ? "dialog" : undefined}
        aria-modal={sheetOpen ? true : undefined}
        aria-label={sheetOpen ? t(sheet === "themes" ? "dashboard.menu" : "dashboard.filters") : undefined}
      >
        <div className="sheet-head">
          <span className="sheet-grip" aria-hidden="true" />
          <h2>{t(sheet === "themes" ? "dashboard.menu" : "dashboard.filters")}</h2>
          <button ref={sheetClose} type="button" className="primary" onClick={() => setSheet(null)}>
            {t(sheet === "themes" ? "dashboard.mobile.close" : "dashboard.mobile.apply")}
          </button>
        </div>
      <Sidebar
        nav={nav}
        onPreload={onPreload}
        municipalStates={states.data ?? []}
        municipalWithin={focus?.startsWith("uf:") ? focus : null}
        onMunicipalState={(key) => { update({ level: "municipio", focus: key }); requestFit(key); }}
        onMunicipalNation={() => { update({ level: "municipio", focus: null }); requestFit(null); }}
        kpi={kpi}
        dimensions={state.dimensions}
        onKpi={(id) => {
          setSheet(null);
          update({ kpi: id, dimensions: [], categories: [], period: null, periods: [], grain: null, correction: null, isolate: false, accumulate: false });
        }}
        onDimensions={(dims) => update({ dimensions: dims, categories: normalizeCategories(kpi, dims, state.categories) })}
        categories={state.categories}
        onDetail={(dims, cats) => update({ dimensions: dims, categories: normalizeCategories(kpi, dims, cats) })}
        level={state.level}
        selection={selection}
        grain={state.grain}
        onGrain={(grain) => update({ grain, period: null, periods: [] })}
        isolate={state.isolate}
        onIsolate={(isolate) => {
          // Isolar: a seleção vira o ano do período atual; sem Isolar, volta ao padrão.
          const years = isolate ? yearsOf([period]) : [];
          update({ isolate, periods: years, period: years.at(-1) ?? null,
            accumulate: canAccumulate(kpi, isolate) && state.accumulate });
        }}
        accumulate={state.accumulate}
        onAccumulate={(accumulate) => update({ accumulate })}
        correction={state.correction}
        onCorrection={(correction) => update({ correction })}
        onLevel={(level) =>
          update({
            level,
            focus: validFocus(ladder, focus, level) ? focus : null,
          })
        }
        onPeriods={(list) => update({ periods: list, period: list.at(-1) ?? null })}
        onClear={clear}
        canClear={filtered}
      />
      </div>
      <main className="main">
        <div className="dash-grid" data-view={view}>
          <div className="area-maphead">
            <div className="page-title">
              <p className="crumb">
                {[crumb, scope, periodLabel].filter(Boolean).join(" · ")}
              </p>
              <h1>
                {kpi.label}
              </h1>
            </div>
            <button type="button" className="small dashboard-reset" disabled={!filtered} onClick={clear}>{t("dashboard.clearFilters")}</button>
          {kpi.map_levels.includes("municipio") && state.geography.startsWith("uf:") && !(state.level === "municipio" && focus === state.geography) ? (
            <div className="map-municipal-action">
              <button type="button" onClick={() => drill(state.geography, "click")}>
                {t("dashboard.focus.municipalities", { state: selectedName })}
              </button>
            </div>
          ) : null}
            {hasMap ? (
              <MapImageExport
                svg={() => svg.current}
                caption={caption}
                filename={`${kpi.kpi_id}_${state.level}${focus ? `_${focus.replace(":", "-")}` : ""}_${period}`}
              />
            ) : null}
          </div>

          <div className="area-views" role="group" aria-label={t("dashboard.mobile.views")}>
            {(["map", "chart", "table"] as const).map((v) => (
              <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)} disabled={v === "map" && !hasMap}>
                {t(`dashboard.mobile.view.${v}`)}
              </button>
            ))}
          </div>

          <section className="area-map" aria-label={t("dashboard.mapTitle")}>
            {!hasMap ? (
              <p className="card muted">{t("dashboard.noMap")}</p>
            ) : geometry.error || values.error ? (
              <Failure
                error={(geometry.error ?? values.error) as Error}
                onRetry={() => setRetry((r) => r + 1)}
              />
            ) : shown ? (
              <MapView
                ref={svg}
                collection={shown.geometry}
                context={shown.context}
                values={shown.values.values}
                selected={state.geography}
                focus={focus}
                canUp={canUp}
                loading={!fresh}
                fitRequest={fit}
                onHover={onHover}
                onSelect={selectOnMap}
                onDrill={drill}
                onUp={up}
                onReset={reset}
                label={caption}
                legendTitle={`${legendTitle}${priced}`}
              >
                <nav
                  className="map-trail"
                  aria-label={t("dashboard.focus.trail")}
                >
                  <ol>
                    <li>
                      {focus ? (
                        <button
                          type="button"
                          onClick={() => {
                            reset();
                            requestFit(null);
                          }}
                        >
                          {t("dashboard.focus.all")}
                        </button>
                      ) : (
                        <span aria-current="location">
                          {t("dashboard.focus.all")}
                        </span>
                      )}
                    </li>
                    {focus
                      ? (trail.data ?? []).map((g, i, chain) => (
                          <li key={g.geography_key}>
                            {i < chain.length - 1 ? (
                              <button
                                type="button"
                                onClick={() => drill(g.geography_key, "click")}
                              >
                                {g.name}
                              </button>
                            ) : (
                              <span aria-current="location">{g.name}</span>
                            )}
                          </li>
                        ))
                      : null}
                    <li className="map-trail-level">{levelLabel}</li>
                  </ol>
                </nav>
              </MapView>
            ) : (
              <p className="card muted" aria-busy="true">
                {t("dashboard.loading")}
              </p>
            )}
          </section>

          {selectedValue ? (
            <div className="area-picked" aria-live="polite">
              <div>
                <strong>{selectedValue.name}</strong>
                <span>
                  {formatValue(selectedValue.value, selectedValue.status)} {unitShort(kpi.unit)}
                </span>
              </div>
              {ladder.includes(levelOf(selectedValue.geography_key)) && nextLevel(ladder, levelOf(selectedValue.geography_key)) ? (
                <button type="button" onClick={() => drill(selectedValue.geography_key, "click")}>
                  {selectedValue.geography_key.startsWith("uf:") ? t("dashboard.focus.municipalities", { state: selectedValue.name }) : t("dashboard.mobile.zoomIn")}
                </button>
              ) : null}
              <button type="button" onClick={() => setView("chart")}>
                {t("dashboard.mobile.seeSeries")}
              </button>
              <button type="button" onClick={() => setView("table")}>
                {t("dashboard.mobile.seeTable")}
              </button>
            </div>
          ) : null}



          <div className="area-datahead">
            <h2 className="data-title">{t("dashboard.chartAndTable")}</h2>
            <DataExport
              key={kpi.kpi_id}
              kpi={kpi}
              level={state.level}
              within={focus}
              periods={selection}
              dimensions={state.dimensions}
              categories={state.categories}
              grain={state.grain}
              correction={state.correction}
            />
          </div>

          <section className={`card area-chart${seasonalMode ? " is-seasonal" : ""}`} aria-labelledby="series-title">
            {!seasonalMode || !seasonal.data || seasonal.error ? chartHeading : null}
            {seasonalMode ? (seasonal.error ? <Failure error={seasonal.error} onRetry={() => setRetry((r) => r + 1)} />
              : seasonal.data ? <SeasonalChart data={seasonal.data} heading={chartHeading} />
              : <p className="muted">{t("dashboard.loading")}</p>) : series.error ? (
              <Failure
                error={series.error}
                onRetry={() => setRetry((r) => r + 1)}
              />
            ) : series.data ? (
              state.isolate ? (
                <SeasonChart data={series.data} accumulated={state.accumulate} />
              ) : (
                <SeriesChart data={series.data} additive={kpi.category_shares} />
              )
            ) : (
              <p className="muted">{t("dashboard.loading")}</p>
            )}
          </section>

          <section
            className={`card area-table${tableWide && !mobile ? " is-wide" : ""}`}
            aria-labelledby="table-title"
            role={tableWide && !mobile ? "region" : undefined}
          >
            <div className="table-head">
              <h2 id="table-title">{`${t("dashboard.tableTitle")} · ${scope} · ${tableLabel}`}</h2>
              {!mobile ? (
                <button
                  ref={tableToggle}
                  type="button"
                  className="table-wide-toggle"
                  aria-pressed={tableWide}
                  onClick={() => setTableWide((v) => !v)}
                >
                  {tableWide ? <CollapseIcon /> : <ExpandIcon />}
                  {tableWide ? t("dashboard.tableCollapse") : t("dashboard.tableExpand")}
                </button>
              ) : null}
            </div>
            <div className="pivot">
              {pivot.data ? null : pivotControls}
              {pivot.error ? (
                <Failure error={pivot.error} onRetry={() => setRetry((r) => r + 1)} />
              ) : pivot.data ? (
                <PivotTable
                  data={pivot.data}
                  totals={Object.fromEntries(kpi.dimensions.map((d) => [d.classification_id, d.total_category_key]))}
                  shares={kpi.category_shares && unitShort(kpi.unit) !== "%"}
                  sharePolicies={Object.fromEntries(kpi.dimensions.map((d) => [d.classification_id, d.share_basis ?? (kpi.category_shares ? "published_total" : "none")]))}
                  dimensionOrder={kpi.dimensions.map((d) => d.classification_id)}
                  selected={state.geography}
                  onSelect={(key) => update({ geography: key })}
                  sources={kpi.source.tables}
                  notes={state.accumulate ? [t("pivot.accumulateNote")] : []}
                  controls={pivotControls}
                />
              ) : (
                <p className="muted">{t("dashboard.loading")}</p>
              )}
            </div>
          </section>

          <div className="area-meta">
            <KpiInfo kpi={kpi} releaseId={nav.release_id} correction={state.correction} dimensions={state.dimensions} />
          </div>
        </div>
      </main>
      <div className="mobile-bar" role="group" aria-label={t("dashboard.mobile.bar")}>
        <button type="button" onClick={() => setSheet("themes")} aria-haspopup="dialog">
          <ListIcon size={18} />
          {t("dashboard.mobile.indicators")}
        </button>
        <button type="button" onClick={() => setSheet("filters")} aria-haspopup="dialog">
          <FilterIcon size={18} />
          {t("dashboard.mobile.filters")}
          {activeFilters ? <span className="mobile-bar-count">{activeFilters}</span> : null}
        </button>
      </div>
      {!coarse && hover && drawn.has(hover.key) ? (
        <DetailTooltip
          name={hover.name}
          detail={batchDetails.get(hover.key) ?? details[detailKey(hover.key)] ?? null}
          loading={!batchDetails.get(hover.key) && !details[detailKey(hover.key)] && !(batch.error || contextBatch.error)}
          error={Boolean(batch.error || contextBatch.error)}
          x={hover.x}
          y={hover.y}
        />
      ) : null}
    </div>
  );
}
