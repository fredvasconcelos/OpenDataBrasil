"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { MapView } from "@/components/MapView";
import { SeriesChart } from "@/components/SeriesChart";
import { ContasPanel, ContasSidebar } from "@/components/contas/ContasPanel";
import { ContasComposition, ContasEmpty, ContasHighlights, ContasRankingTable, ContasTooltip, ContasUnavailable, PeriodStatusList } from "@/components/contas/ContasParts";
import { api } from "@/lib/api";
import { contasApi } from "@/lib/api/contas";
import { pointAt, toMapValues, toSeries } from "@/lib/contas/adapt";
import { periodLabel } from "@/lib/contas/format";
import { availablePeriods, findState, readContasState } from "@/lib/contas/state";
import type { ContasMeta } from "@/lib/contas/types";
import { useAsync } from "@/lib/useAsync";

/** Carregamento independente: falhas das contas não impedem o bloco de Estatísticas. */
export function ContasDashboard() {
  const t = useTranslations("contas");
  const [retry, setRetry] = useState(0);
  const meta = useAsync(contasApi.meta, [], retry);
  if (meta.loading) return <p className="page" role="status">{t("loading")}</p>;
  if (!meta.data) return <main className="page"><ContasUnavailable onRetry={() => setRetry((n) => n + 1)} /></main>;
  return <LoadedDashboard key={`${meta.data.release_id}:${retry}`} meta={meta.data} onRetry={() => setRetry((n) => n + 1)} />;
}

function LoadedDashboard({ meta, onRetry }: { meta: ContasMeta; onRetry: () => void }) {
  const t = useTranslations("contas");
  const search = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const state = readContasState(new URLSearchParams(search), meta);
  const { geography, period, area, page, grain } = state;
  const [hover, setHover] = useState<{ key: string; name: string; x: number; y: number } | null>(null);
  const change = (values: Record<string, string | number | null>) => {
    const next = new URLSearchParams(search);
    for (const [key, value] of Object.entries(values)) {
      if (value === null) next.delete(key); else next.set(key, String(value));
    }
    router.push(`${path}?${next}`, { scroll: false });
  };
  const loaded = useAsync(async () => {
    const selected = await api.geography(geography);
    const municipality = selected.level_id === "municipio";
    const parent = municipality ? await findState(selected, api.geography) : null;
    const within = municipality ? parent?.geography_key : selected.level_id === "uf" ? geography : null;
    if (municipality && !within) throw new Error("territory_unavailable");
    const level = within ? "municipio" : "uf";
    const filters = area ? { dimension: "function", categories: [area] } : {};
    const [map, collection, states, composition, byType, series, totalSeries, ranking] = await Promise.all([
      contasApi.map({ level, within, periods: [period], ...filters }),
      api.geometry(level, within),
      api.geographies("uf"),
      contasApi.composition(geography, [period]),
      contasApi.series({ geography_key: geography, periods: [period], grain: period.length === 4 ? "ano" : "mes", dimension: "transfer_type" }),
      contasApi.series({ geography_key: geography, periods: [period], grain, ...filters }),
      contasApi.series({ geography_key: geography, periods: [period], grain: period.length === 4 ? "ano" : "mes", ...filters }),
      contasApi.ranking(geography, Number(period.slice(0, 4)), page),
    ]);
    // Se um release trocar durante as chamadas, recarrega o bloco inteiro antes de exibir.
    if ([map, composition, byType, series, totalSeries, ranking].some((r) => r.provenance.release_id !== meta.release_id)) throw new Error("release_changed");
    return { selected, parent, within, map, collection, states, composition, byType, series, ranking, total: pointAt(totalSeries, area ?? "total", period) };
  }, [geography, period, area, page, grain, meta.release_id]);

  const data = loaded.data;
  const trail = [{ key: "brasil:1", label: t("brasil") }, ...(data?.parent ? [{ key: data.parent.geography_key, label: data.parent.name }] : []), ...(data && geography !== "brasil:1" ? [{ key: geography, label: data.selected.name }] : [])];
  const territories = data ? [...data.states.map((x) => ({ key: x.geography_key, label: x.name })), ...(data.within ? data.map.rows.map((r) => ({ key: r.geography_key, label: r.name })) : [])] : [];
  const areaOptions = data?.composition.rows.filter((r) => r.category_code && !r.label.startsWith("Demais")).map((r) => ({ code: r.category_code, label: r.label })) ?? [];
  const name = data?.selected.name ?? geography;
  const hovered = data?.map.rows.find((r) => r.geography_key === hover?.key);
  const selectedArea = areaOptions.find((a) => a.code === area)?.label ?? area;
  const periodNotes = meta.lenses.find((l) => l.lens === "A")?.statuses.filter((s) => data?.series.provenance.periods.includes(s.period)) ?? [];
  const hasTesouro = periodNotes.some((s) => s.note.includes("Tesouro"));
  const up = () => change({ geography: data?.parent?.geography_key ?? "brasil:1", page: 1 });
  return (
    <main className="contas-dashboard">
      <ContasSidebar trail={trail} territories={territories} period={period} periods={availablePeriods(meta).map((code) => ({ code, label: periodLabel(code) }))} areas={areaOptions} area={area}
        onTerritory={(key) => change({ geography: key || "brasil:1", page: 1 })} onPeriod={(code) => change({ period: code, page: 1 })} onArea={(code) => change({ area: code || null, page: 1 })} />
      {loaded.loading ? <p className="page" role="status">{t("loading")}</p> : !data ? <div className="page"><ContasUnavailable onRetry={onRetry} /><button type="button" className="btn-outline" onClick={() => router.replace(path)}>{t("resetFilters")}</button></div> : (
        <ContasPanel crumb={t("lensName")} title={t("scope", { territory: name, period: periodLabel(period) })}
          status={<PeriodStatusList provenance={data.series.provenance} />}
          highlights={data.total === null ? <p role="status">{t("totalUnavailable")}</p> : <ContasHighlights total={data.total} byType={area ? null : data.byType} composition={area ? null : data.composition} year={period} />}
          map={<>
            <nav className="contas-trail" aria-label={t("territoryTrail")}>{trail.map((item) => <button key={item.key} type="button" aria-current={item.key === geography ? "location" : undefined} onClick={() => change({ geography: item.key, page: 1 })}>{item.label}</button>)}</nav>
            {area ? <p className="contas-hint">{t("filteredArea", { area: selectedArea ?? "" })}</p> : null}
            <div className="contas-map-wrap">
              <MapView groupedControls collection={data.collection} context={null} values={toMapValues(data.map)} selected={geography} focus={data.within ?? null} canUp={geography !== "brasil:1"}
                onHover={(key, label, event) => setHover(key ? { key, name: label, x: event.clientX, y: event.clientY } : null)}
                onSelect={(key) => change({ geography: key, page: 1 })} onDrill={(key) => { change({ geography: key, page: 1 }); return true; }} onUp={up} onReset={() => change({ geography: "brasil:1", page: 1 })}
                label={t("map.title")} legendTitle={t("map.legend")} />
            </div>
            {hover && hovered ? <div className="contas-tooltip-position" style={{ left: Math.max(8, Math.min(hover.x + 12, (typeof window === "undefined" ? 1024 : window.innerWidth) - 320)), top: Math.max(8, Math.min(hover.y + 12, (typeof window === "undefined" ? 768 : window.innerHeight) - 240)) }}><ContasTooltip name={hover.name} value={hovered.value} period={periodLabel(period)} inline /></div> : null}
            {!data.map.rows.length && data.total === null ? <ContasEmpty /> : null}
            <p className="contas-hint" role="note">{t("map.note")}</p><p className="contas-hint">{t("mapTotalNote")}</p>
          </>}
          how={<><p className="contas-hint">{t("allAreasContext")}</p><ContasComposition byType={data.byType} composition={data.composition} year={period} area={area} onArea={(code) => change({ area: code === area ? null : code, page: 1 })} /></>}
          when={<><label className="field">{t("grain")}<select value={grain} onChange={(e) => change({ grain: e.target.value })}><option value="mes">{t("when.monthly")}</option><option value="ano">{t("when.yearly")}</option></select></label><div className="contas-series-wrap"><SeriesChart data={toSeries(data.series, name)} /></div></>}
          who={<><p className="contas-hint" role="note">{t("rankingScope", { year: period.slice(0, 4) })}</p><ContasRankingTable ranking={data.ranking} onPage={(n) => change({ page: n })} hrefOf={(id) => `/contas/favorecidos/${id}?year=${period.slice(0, 4)}`} />{data.ranking.notes.map((note) => <p key={note} className="contas-hint" role="note">{note}</p>)}</>}
          foot={<><p>{t("source")}</p>{hasTesouro ? <p>{t("tesouro")}</p> : null}<p>{t("release")}: <code>{data.series.provenance.release_id}</code></p><details><summary>{t("notes")}</summary>{periodNotes.filter((n) => n.note).map((n) => <p key={n.period}>{periodLabel(n.period)}: {n.note}</p>)}{meta.lenses.find((l) => l.lens === "A")?.notes.map((note) => <p key={note}>{note}</p>)}{data.series.provenance.tables.map((table) => <p key={table.table_id}>{table.table_id}: {table.delta_version}</p>)}</details></>} />
      )}
    </main>
  );
}
