"use client";

import { useTranslations } from "next-intl";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useRef, useState } from "react";

import { DataTable } from "@/components/DataTable";
import { DetailTooltip } from "@/components/DetailTooltip";
import { DataExport, MapImageExport } from "@/components/ExportMenu";
import { KpiInfo } from "@/components/KpiInfo";
import { MapView, type FitRequest } from "@/components/MapView";
import { SeriesChart } from "@/components/SeriesChart";
import { Sidebar } from "@/components/Sidebar";
import { api } from "@/lib/api";
import { formatPeriod, legendTitleKey } from "@/lib/format";
import {
  allKpis,
  DEFAULT_GEOGRAPHY,
  readState,
  writeState,
  type DashboardState,
} from "@/lib/state";
import type {
  Detail,
  GeoCollection,
  Geography,
  MapData,
  Navigation,
} from "@/lib/types";
import { useAsync } from "@/lib/useAsync";
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
        {t("error")} <span className="small">({error.message})</span>
      </span>
      <button type="button" className="primary" onClick={onRetry}>
        {t("retry")}
      </button>
    </div>
  );
}

export function Dashboard({ nav }: { nav: Navigation }) {
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const state = useMemo(
    () => readState(new URLSearchParams(params.toString()), nav),
    [params, nav],
  );
  const kpi = useMemo(
    () => allKpis(nav).find((k) => k.kpi_id === state.kpi) ?? null,
    [nav, state.kpi],
  );
  const [retry, setRetry] = useState(0);
  // Página da tabela. `locate`: território clicado no mapa; a API devolve a página
  // que o contém (na mesma ordenação) e a tabela rola até a linha.
  const [sort, setSort] = useState<{
    sort: "value" | "name";
    order: "asc" | "desc";
    offset: number;
    locate: string | null;
  }>({ sort: "value", order: "desc", offset: 0, locate: null });
  const [hover, setHover] = useState<Hover | null>(null);
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
      router.replace(`${pathname}?${writeState(next)}`, { scroll: false });
      // Trocar só o território selecionado não muda a tabela (nem a página dela).
      if (Object.keys(patch).some((k) => k !== "geography"))
        setSort((s) => ({ ...s, offset: 0, locate: null }));
    },
    [state, router, pathname],
  );

  const hasMap = Boolean(kpi?.map_levels.includes(state.level));
  const kpiId = kpi?.kpi_id ?? null;
  const focus = state.focus;
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
            period: state.period,
            within: focus,
          })
      : null,
    [kpiId, state.level, state.period, focus],
    retry,
  );
  // Trilha do recorte (ex.: Norte › Amazonas), pelos territórios pais publicados na Gold.
  const ladder = useMemo(() => zoomLadder(kpi?.map_levels ?? []), [kpi]);
  const trail = useAsync(
    focus
      ? async () => {
          const chain: Geography[] = [];
          let key: string | null = focus;
          while (key && ladder.includes(levelOf(key)) && chain.length < 4) {
            const g: Geography = await api.geography(key);
            chain.unshift(g);
            key = g.parent_key;
          }
          return chain;
        }
      : null,
    [focus, ladder.join()],
  );
  const series = useAsync(
    kpiId
      ? () =>
          api.series(kpiId, {
            geography: state.geography,
            dimensions: state.dimensions,
          })
      : null,
    [kpiId, state.geography, state.dimensions.join()],
    retry,
  );
  const table = useAsync(
    kpiId
      ? () =>
          api.table(kpiId, {
            level: state.level,
            period: state.period,
            within: focus,
            dimensions: state.dimensions,
            sort: sort.sort,
            order: sort.order,
            offset: sort.offset,
            locate: sort.locate,
            limit: 50,
          })
      : null,
    [
      kpiId,
      state.level,
      state.period,
      focus,
      state.dimensions.join(),
      sort.sort,
      sort.order,
      sort.offset,
      sort.locate,
    ],
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
    `${kpiId}|${state.period ?? ""}|${state.dimensions.join()}|${geo}`;
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
    setHover({ key, name, x: e.clientX, y: e.clientY });
    const cacheKey = detailKey(key);
    if (details[cacheKey]) return;
    pending.current = setTimeout(() => {
      api
        .detail(kpiId, {
          geography: key,
          period: state.period,
          dimensions: state.dimensions,
        })
        .then((d) => setDetails((all) => ({ ...all, [cacheKey]: d })))
        .catch(() => undefined);
    }, 120);
  };

  if (!kpi) return <p className="page">{t("dashboard.selectKpi")}</p>;
  const period = state.period ?? kpi.periods.at(-1) ?? "";
  const periodLabel = formatPeriod(period);
  const levelLabel = t(`levels.${state.level}`);
  const crumb =
    nav.themes
      .flatMap((th) =>
        th.subthemes
          .filter((s) => s.kpis.some((k) => k.kpi_id === kpi.kpi_id))
          .map((s) => `${th.label} › ${s.label}`),
      )
      .at(0) ?? "";
  const selectedName =
    state.geography === DEFAULT_GEOGRAPHY
      ? t("levels.brasil")
      : (values.data?.values.find((v) => v.geography_key === state.geography)
          ?.name ??
        shown?.context?.features.find((f) => f.id === state.geography)
          ?.properties.name ??
        series.data?.geography.name ??
        state.geography);
  const defaults = readState(new URLSearchParams({ kpi: kpi.kpi_id }), nav);
  const filtered = writeState(state) !== writeState(defaults);
  const clear = () => {
    update(defaults);
    setSort({ sort: "value", order: "desc", offset: 0, locate: null });
    requestFit(null);
  };
  // Clique no mapa: seleciona e localiza o território na tabela.
  const selectOnMap = (key: string) => {
    update({ geography: key });
    setSort((cur) => ({ ...cur, locate: key }));
  };
  const focusName = focus ? (trail.data?.at(-1)?.name ?? null) : null;
  const scope = `${levelLabel}${focusName ? ` · ${focusName}` : ""}`;
  const caption = `${kpi.label} · ${scope} · ${periodLabel} · Fonte: IBGE, tabela ${kpi.source.source_table_id} · release ${nav.release_id}`;
  const legendKey = legendTitleKey(kpi.unit);
  // KPIs cujo Total é só o universo: o mapa mostra o % de uma categoria (map_share).
  const legendTitle =
    values.data?.measure === "share" && values.data.measure_label
      ? values.data.measure_label
      : legendKey
        ? t(`dashboard.legend.title.${legendKey}`)
        : kpi.unit;

  // Painel (Design System ODBr v2): filtros na barra lateral; exportações junto do
  // que exportam (imagem → cabeçalho do mapa; dados → "Gráfico e tabela"). Layout
  // por CSS (.dash-grid): empilhado até 1599 px; tela cheia sem rolagem a partir de
  // 1600 px (mapa à esquerda, gráfico e tabela à direita, fonte no rodapé).
  return (
    <div className="dashboard">
      <Sidebar
        nav={nav}
        kpi={kpi}
        dimensions={state.dimensions}
        onKpi={(id) => update({ kpi: id, dimensions: [], period: null })}
        onDimensions={(dims) => update({ dimensions: dims })}
        level={state.level}
        period={period}
        onLevel={(level) =>
          update({
            level,
            focus: validFocus(ladder, focus, level) ? focus : null,
          })
        }
        onPeriod={(p) => update({ period: p })}
        onClear={clear}
        canClear={filtered}
      />
      <main className="main">
        <div className="dash-grid">
          <div className="area-maphead">
            <div className="page-title">
              <p className="crumb">
                {[crumb, scope, periodLabel].filter(Boolean).join(" · ")}
              </p>
              <h1>{kpi.label}</h1>
            </div>
            {hasMap ? (
              <MapImageExport
                svg={() => svg.current}
                caption={caption}
                filename={`${kpi.kpi_id}_${state.level}${focus ? `_${focus.replace(":", "-")}` : ""}_${period}`}
              />
            ) : null}
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
                legendTitle={legendTitle}
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

          <div className="area-datahead">
            <h2 className="data-title">{t("dashboard.chartAndTable")}</h2>
            <DataExport
              kpiId={kpi.kpi_id}
              level={state.level}
              within={focus}
              period={period}
              dimensions={state.dimensions}
            />
          </div>

          <section className="card area-chart" aria-labelledby="series-title">
            <h2 id="series-title">
              {t("dashboard.seriesTitle")} · {selectedName}{" "}
              {state.geography !== DEFAULT_GEOGRAPHY ? (
                <button
                  type="button"
                  className="small"
                  onClick={() => update({ geography: DEFAULT_GEOGRAPHY })}
                >
                  {t("dashboard.resetSelection")}
                </button>
              ) : null}
            </h2>
            {series.error ? (
              <Failure
                error={series.error}
                onRetry={() => setRetry((r) => r + 1)}
              />
            ) : series.data ? (
              <SeriesChart data={series.data} />
            ) : (
              <p className="muted">{t("dashboard.loading")}</p>
            )}
          </section>

          <section className="card area-table" aria-labelledby="table-title">
            <h2 id="table-title">
              {t("dashboard.tableTitle")} · {scope} · {periodLabel}
            </h2>
            {table.error ? (
              <Failure
                error={table.error}
                onRetry={() => setRetry((r) => r + 1)}
              />
            ) : table.data ? (
              <DataTable
                data={table.data}
                selected={state.geography}
                sort={sort.sort}
                order={sort.order}
                onSort={(s) =>
                  setSort((cur) => ({
                    sort: s,
                    order:
                      cur.sort === s && cur.order === "desc"
                        ? "asc"
                        : s === "name"
                          ? "asc"
                          : "desc",
                    offset: 0,
                    locate: null,
                  }))
                }
                onPage={(offset) =>
                  setSort((cur) => ({ ...cur, offset, locate: null }))
                }
                onSelect={(key) => update({ geography: key })}
              />
            ) : (
              <p className="muted">{t("dashboard.loading")}</p>
            )}
          </section>

          <div className="area-meta">
            <KpiInfo kpi={kpi} releaseId={nav.release_id} />
          </div>
        </div>
      </main>
      {hover && drawn.has(hover.key) ? (
        <DetailTooltip
          name={hover.name}
          detail={details[detailKey(hover.key)] ?? null}
          loading={!details[detailKey(hover.key)]}
          x={hover.x}
          y={hover.y}
        />
      ) : null}
    </div>
  );
}
