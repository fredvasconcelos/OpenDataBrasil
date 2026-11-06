"use client";

import { useTranslations } from "next-intl";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useRef, useState } from "react";

import { DataTable } from "@/components/DataTable";
import { DetailTooltip } from "@/components/DetailTooltip";
import { ExportMenu } from "@/components/ExportMenu";
import { KpiInfo } from "@/components/KpiInfo";
import { MapView } from "@/components/MapView";
import { SeriesChart } from "@/components/SeriesChart";
import { Sidebar } from "@/components/Sidebar";
import { api } from "@/lib/api";
import { allKpis, DEFAULT_GEOGRAPHY, readState, writeState, type DashboardState } from "@/lib/state";
import type { Detail, Navigation } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

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
      {t("error")} <span className="small">({error.message})</span>{" "}
      <button type="button" onClick={onRetry}>
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
  const state = useMemo(() => readState(new URLSearchParams(params.toString()), nav), [params, nav]);
  const kpi = useMemo(() => allKpis(nav).find((k) => k.kpi_id === state.kpi) ?? null, [nav, state.kpi]);
  const [retry, setRetry] = useState(0);
  const [sort, setSort] = useState<{ sort: "value" | "name"; order: "asc" | "desc"; offset: number }>({
    sort: "value",
    order: "desc",
    offset: 0,
  });
  const [hover, setHover] = useState<Hover | null>(null);
  const [details, setDetails] = useState<Record<string, Detail>>({});
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);
  const svg = useRef<SVGSVGElement>(null);

  const update = useCallback(
    (patch: Partial<DashboardState>) => {
      const next = { ...state, ...patch };
      router.replace(`${pathname}?${writeState(next)}`, { scroll: false });
      setSort((s) => ({ ...s, offset: 0 }));
    },
    [state, router, pathname],
  );

  const hasMap = Boolean(kpi?.map_levels.includes(state.level));
  const kpiId = kpi?.kpi_id ?? null;
  const geometry = useAsync(hasMap ? () => api.geometry(state.level) : null, [state.level, hasMap], retry);
  const values = useAsync(
    kpiId ? () => api.map(kpiId, { level: state.level, period: state.period }) : null,
    [kpiId, state.level, state.period],
    retry,
  );
  const series = useAsync(
    kpiId ? () => api.series(kpiId, { geography: state.geography, dimensions: state.dimensions }) : null,
    [kpiId, state.geography, state.dimensions.join()],
    retry,
  );
  const table = useAsync(
    kpiId
      ? () =>
          api.table(kpiId, {
            level: state.level,
            period: state.period,
            dimensions: state.dimensions,
            sort: sort.sort,
            order: sort.order,
            offset: sort.offset,
            limit: 50,
          })
      : null,
    [kpiId, state.level, state.period, state.dimensions.join(), sort.sort, sort.order, sort.offset],
    retry,
  );

  const detailKey = (geo: string) => `${kpiId}|${state.period ?? ""}|${state.dimensions.join()}|${geo}`;
  const onHover = (key: string | null, name: string, e: { clientX: number; clientY: number }) => {
    if (pending.current) clearTimeout(pending.current);
    if (!key || !kpiId) {
      setHover(null);
      return;
    }
    setHover({ key, name, x: e.clientX, y: e.clientY });
    const cacheKey = detailKey(key);
    if (details[cacheKey]) return;
    pending.current = setTimeout(() => {
      api
        .detail(kpiId, { geography: key, period: state.period, dimensions: state.dimensions })
        .then((d) => setDetails((all) => ({ ...all, [cacheKey]: d })))
        .catch(() => undefined);
    }, 120);
  };

  if (!kpi) return <p className="page">{t("dashboard.selectKpi")}</p>;
  const levels = kpi.levels;
  const periods = kpi.periods;
  const period = state.period ?? periods.at(-1) ?? "";
  const selectedName =
    state.geography === DEFAULT_GEOGRAPHY
      ? t("levels.brasil")
      : (values.data?.values.find((v) => v.geography_key === state.geography)?.name ??
        series.data?.geography.name ??
        state.geography);
  const caption = `${kpi.label} · ${t(`levels.${state.level}`)} · ${period} · Fonte: IBGE, tabela ${kpi.source.source_table_id} · release ${nav.release_id}`;

  return (
    <div className="dashboard">
      <Sidebar
        nav={nav}
        kpi={kpi}
        dimensions={state.dimensions}
        onKpi={(id) => update({ kpi: id, dimensions: [], period: null })}
        onDimensions={(dims) => update({ dimensions: dims })}
      />
      <main className="main">
        <div className="toolbar">
          <h1>{kpi.label}</h1>
          <label>
            {t("dashboard.level")}
            <select value={state.level} onChange={(e) => update({ level: e.target.value })}>
              {levels.map((l) => (
                <option key={l} value={l}>
                  {t(`levels.${l}`)}
                  {kpi.map_levels.includes(l) ? "" : " (sem mapa)"}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("dashboard.period")}
            <select value={period} onChange={(e) => update({ period: e.target.value })}>
              {periods.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
        </div>

        <section aria-label={t("dashboard.mapTitle")}>
          {!hasMap ? (
            <p className="card muted">{t("dashboard.noMap")}</p>
          ) : geometry.error || values.error ? (
            <Failure error={(geometry.error ?? values.error) as Error} onRetry={() => setRetry((r) => r + 1)} />
          ) : geometry.data && values.data ? (
            <MapView
              ref={svg}
              collection={geometry.data}
              values={values.data.values}
              selected={state.geography}
              onHover={onHover}
              onSelect={(key) => update({ geography: key })}
              label={caption}
            />
          ) : (
            <p className="card muted" aria-busy="true">
              {t("dashboard.loading")}
            </p>
          )}
        </section>
        {hover ? (
          <DetailTooltip
            name={hover.name}
            detail={details[detailKey(hover.key)] ?? null}
            loading={!details[detailKey(hover.key)]}
            x={hover.x}
            y={hover.y}
          />
        ) : null}

        <ExportMenu
          kpiId={kpi.kpi_id}
          level={state.level}
          period={period}
          dimensions={state.dimensions}
          svg={() => svg.current}
          caption={caption}
          filename={`${kpi.kpi_id}_${state.level}_${period}`}
        />

        <div className="bottom">
          <section className="card" aria-labelledby="series-title">
            <h2 id="series-title" style={{ fontSize: 15, marginTop: 0 }}>
              {t("dashboard.seriesTitle")} · {selectedName}{" "}
              {state.geography !== DEFAULT_GEOGRAPHY ? (
                <button type="button" className="small" onClick={() => update({ geography: DEFAULT_GEOGRAPHY })}>
                  {t("dashboard.resetSelection")}
                </button>
              ) : null}
            </h2>
            {series.error ? (
              <Failure error={series.error} onRetry={() => setRetry((r) => r + 1)} />
            ) : series.data ? (
              <SeriesChart data={series.data} />
            ) : (
              <p className="muted">{t("dashboard.loading")}</p>
            )}
          </section>
          <section className="card" aria-labelledby="table-title">
            <h2 id="table-title" style={{ fontSize: 15, marginTop: 0 }}>
              {t("dashboard.tableTitle")} · {t(`levels.${state.level}`)} · {period}
            </h2>
            {table.error ? (
              <Failure error={table.error} onRetry={() => setRetry((r) => r + 1)} />
            ) : table.data ? (
              <DataTable
                data={table.data}
                selected={state.geography}
                sort={sort.sort}
                order={sort.order}
                onSort={(s) =>
                  setSort((cur) => ({
                    sort: s,
                    order: cur.sort === s && cur.order === "desc" ? "asc" : s === "name" ? "asc" : "desc",
                    offset: 0,
                  }))
                }
                onPage={(offset) => setSort((cur) => ({ ...cur, offset }))}
                onSelect={(key) => update({ geography: key })}
              />
            ) : (
              <p className="muted">{t("dashboard.loading")}</p>
            )}
          </section>
        </div>

        <KpiInfo kpi={kpi} releaseId={nav.release_id} />
      </main>
    </div>
  );
}
