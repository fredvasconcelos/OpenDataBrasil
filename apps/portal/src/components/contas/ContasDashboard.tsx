"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { FederalDashboard } from "@/components/contas/FederalDashboard";
import { MapView } from "@/components/MapView";
import { SeriesChart } from "@/components/SeriesChart";
import { ContasPanel, ContasSidebar } from "@/components/contas/ContasPanel";
import { ContasReferences } from "@/components/contas/ContasReferences";
import { contasTooltipPosition, ContasComposition, ContasEmpty, ContasHighlights, ContasRankingTable, ContasTooltip, ContasUnavailable, PeriodStatusList } from "@/components/contas/ContasParts";
import { api } from "@/lib/api";
import { contasApi } from "@/lib/api/contas";
import { toMapValues, toSeries } from "@/lib/contas/adapt";
import { periodLabel } from "@/lib/contas/format";
import { availablePeriods, defaultPeriod, findState, panelHref, readContasState } from "@/lib/contas/state";
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
  const search = useSearchParams();
  const lens = search.get("lens") === "B" ? "B" : search.get("lens") === "C" ? "C" : "A";
  return <>{lens === "A" ? <TransfersDashboard meta={meta} onRetry={onRetry} /> : <FederalDashboard key={lens} meta={meta} lens={lens} onRetry={onRetry} />}</>;
}

function TransfersDashboard({ meta, onRetry }: { meta: ContasMeta; onRetry: () => void }) {
  const t = useTranslations("contas");
  const search = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const state = readContasState(new URLSearchParams(search), meta);
  const { geography, period, area, page, grain, order } = state;
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
    const [map, collection, context, states, composition, byType, series, ranking] = await Promise.all([
      contasApi.map({ level, within, periods: [period], ...filters }),
      api.geometry(level, within),
      within ? api.geometry("uf") : null,
      api.geographies("uf"),
      contasApi.areas(geography, [period]),
      contasApi.table({ geography_key: geography, periods: [period], group_by: "transfer_type", filter: area ? [`function:${area}`] : [] }),
      contasApi.series({ geography_key: geography, periods: [period], grain, ...filters }),
      contasApi.table({ geography_key: geography, periods: [period], group_by: "recipient", filter: area ? [`function:${area}`] : [], page, sort: order }),
    ]);
    // Se um release trocar durante as chamadas, recarrega o bloco inteiro antes de exibir.
    if ([map, composition, byType, series, ranking].some((r) => r.provenance.release_id !== meta.release_id)) throw new Error("release_changed");
    return { scope: state, selected, parent, within, map, collection, context, states, composition, byType, series, ranking, total: byType.value_total };
  }, [geography, period, area, page, grain, order, meta.release_id], 0, true);

  const data = loaded.data;
  // Os links do catálogo (#onde, #quando, #quem, #como) apontam para seções que só existem
  // depois da primeira carga; rola até elas uma vez, quando aparecem.
  const jumped = useRef(false);
  useEffect(() => {
    if (!data || jumped.current) return;
    jumped.current = true;
    const target = window.location.hash ? document.getElementById(decodeURIComponent(window.location.hash.slice(1))) : null;
    target?.scrollIntoView({ block: "start" });
  }, [data]);
  // Mantém o contexto dos valores anteriores durante a atualização dos filtros.
  const displayed = data?.scope ?? state;
  const trail = [{ key: "brasil:1", label: t("brasil") }, ...(data?.parent ? [{ key: data.parent.geography_key, label: data.parent.name }] : []), ...(data && displayed.geography !== "brasil:1" ? [{ key: displayed.geography, label: data.selected.name }] : [])];
  const territories = data ? [...data.states.map((x) => ({ key: x.geography_key, label: x.name })), ...(data.within ? data.map.rows.map((r) => ({ key: r.geography_key, label: r.name })) : [])] : [];
  const areaOptions = data?.composition.rows.map((r) => ({ code: r.key, label: r.label })) ?? [];
  const name = data?.selected.name ?? geography;
  const hovered = data?.map.rows.find((r) => r.geography_key === hover?.key);
  const selectedArea = areaOptions.find((a) => a.code === displayed.area)?.label ?? displayed.area;
  const periodNotes = meta.lenses.find((l) => l.lens === "A")?.statuses.filter((s) => data?.series.provenance.periods.includes(s.period)) ?? [];
  const hasTesouro = periodNotes.some((s) => s.note.includes("Tesouro"));
  const up = () => change({ geography: data?.parent?.geography_key ?? "brasil:1", page: 1 });
  const profileHref = (id: string) => {
    const filters = new URLSearchParams(search);
    filters.set("geography", geography);
    filters.set("period", period);
    const query = new URLSearchParams({ year: period.slice(0, 4), back: panelHref(filters) });
    return `/contas/favorecidos/${encodeURIComponent(id)}?${query}`;
  };
  return (
    <div className="dashboard contas-dashboard">
      <ContasSidebar meta={meta} trail={trail} territories={territories} period={period} periods={availablePeriods(meta).map((code) => ({ code, label: periodLabel(code) }))} areas={areaOptions} area={area}
        onTerritory={(key) => change({ geography: key || "brasil:1", page: 1 })} onPeriod={(code) => change({ period: code, page: 1 })} onArea={(code) => change({ area: code || null, page: 1 })} onClear={() => router.push(path, { scroll: false })} canClear={geography !== "brasil:1" || period !== defaultPeriod(meta) || area !== null || page !== 1 || grain !== "mes" || order !== "value"} />
      <main className="main contas-content" aria-busy={loaded.loading}>
      {loaded.loading && !data ? <p role="status">{t("loading")}</p> : !data ? <div><ContasUnavailable onRetry={onRetry} /><button type="button" className="btn-outline" onClick={() => router.replace(path)}>{t("resetFilters")}</button></div> : (
        <>
        <p className="contas-update" role="status">{loaded.loading ? t("updating") : ""}</p>
        <ContasPanel crumb={`${t("blockName")} · ${t("lensName")}`} title={t("scope", { territory: name, period: periodLabel(displayed.period) })}
          status={<PeriodStatusList provenance={data.series.provenance} />}
          highlights={<ContasHighlights total={data.total} byType={data.byType} />}
          map={<>
            <div className="contas-map-wrap">
              <MapView groupedControls collection={data.collection} context={data.context} values={toMapValues(data.map)} selected={displayed.geography} focus={data.within ?? null} fitRequest={{ key: data.within ?? null, n: 0 }} canUp={displayed.geography !== "brasil:1"} loading={loaded.loading}
                onHover={(key, label, event) => setHover(key ? { key, name: label, x: event.clientX, y: event.clientY } : null)}
                onSelect={(key) => change({ geography: key, page: 1 })} onDrill={(key) => { change({ geography: key, page: 1 }); return true; }} onUp={up} onReset={() => change({ geography: "brasil:1", page: 1 })}
                label={t("map.title")} legendTitle={t("map.legend")}>
                {/* Trilha do recorte dentro do mapa, como no Painel das Estatísticas. */}
                <nav className="map-trail" aria-label={t("territoryTrail")}>
                  <ol>
                    {trail.map((item, i) => (
                      <li key={item.key ?? i}>
                        {i < trail.length - 1 ? <button type="button" onClick={() => change({ geography: item.key, page: 1 })}>{item.label}</button> : <span aria-current="location">{item.label}</span>}
                      </li>
                    ))}
                  </ol>
                </nav>
              </MapView>
            </div>
            {hover && hovered ? <div className="contas-tooltip-position" style={contasTooltipPosition(hover)}><ContasTooltip name={hover.name} value={hovered.value} period={periodLabel(displayed.period)} inline /></div> : null}
            {!data.map.rows.length && data.total === 0 ? <ContasEmpty /> : null}
          </>}
          how={<><ContasComposition byType={data.byType} composition={data.composition} area={displayed.area} onArea={(code) => change({ area: code === area ? null : code, page: 1 })} /></>}
          when={<><label className="field">{t("grain")}<select value={grain} onChange={(e) => change({ grain: e.target.value })}><option value="mes">{t("when.monthly")}</option><option value="ano">{t("when.yearly")}</option></select></label><div className="contas-series-wrap"><SeriesChart data={toSeries(data.series, name, displayed.area)} /></div></>}
          who={<ContasRankingTable table={data.ranking} territory={name} scope={`${name} · ${periodLabel(displayed.period)} · ${selectedArea ?? t("allAreas")}`} order={displayed.order} onOrder={(o) => change({ order: o === "value" ? null : o, page: 1 })} onPage={(n) => change({ page: n })} hrefOf={profileHref} />}
          scope={displayed.area ? selectedArea : null}
          info={{
            map: <>
              <p>{t("map.note")}</p>
              <p>{t("mapTotalNote")}</p>
              {displayed.area ? <p>{t("filteredArea", { area: selectedArea ?? "" })}</p> : null}
            </>,
            how: <>
              <p>{displayed.area ? t("typeAreaContext", { area: selectedArea ?? "" }) : t("allAreasContext")}</p>
              <p>{t("how.areaHint")}</p>
            </>,
            when: <>
              <p>{t("whenNote")}</p>
              {periodNotes.filter((n) => n.note).map((n) => <p key={n.period}><strong>{periodLabel(n.period)}:</strong> {n.note}</p>)}
            </>,
          }}
          foot={<section className="card meta" aria-labelledby="contas-meta-title">
            <h2 id="contas-meta-title" className="sr-only">{t("sourcesTitle")}</h2>
            <p className="meta-source">
              <strong>{t("sourceLabel")}:</strong> {t("sourceBody")}{hasTesouro ? ` · ${t("tesouroShort")}` : ""} · {t("release")} <code>{data.series.provenance.release_id.slice(0, 8)}</code>
            </p>
            <details className="meta-more">
              <summary>{t("notes")}</summary>
              <div className="meta-body">
                <p>{t("map.note")}</p>
                <p>{t("mapTotalNote")}</p>
                {hasTesouro ? <p>{t("tesouro")}</p> : null}
                {periodNotes.filter((n) => n.note).map((n) => <p key={n.period}>{periodLabel(n.period)}: {n.note}</p>)}
                {data.ranking.notes.map((note) => <p key={note}>{note}</p>)}
                {meta.lenses.find((l) => l.lens === "A")?.notes.map((note) => <p key={note}>{note}</p>)}
                <p>{t("release")}: <code>{data.series.provenance.release_id}</code></p>
                <ul className="small">{data.series.provenance.tables.map((table) => <li key={table.table_id}>{table.table_id}: {table.delta_version}</li>)}</ul>
                <ContasReferences />
              </div>
            </details>
          </section>} />
        </>
      )}
      </main>
    </div>
  );
}
