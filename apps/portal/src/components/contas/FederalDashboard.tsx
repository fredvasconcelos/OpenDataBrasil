"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { MapView } from "@/components/MapView";
import { SeriesChart } from "@/components/SeriesChart";
import { ContasReferences } from "@/components/contas/ContasReferences";
import { ContasTooltip, ContasUnavailable, PeriodStatusList } from "@/components/contas/ContasParts";
import { api } from "@/lib/api";
import { contasApi } from "@/lib/api/contas";
import { toMapValues, toSeries } from "@/lib/contas/adapt";
import { brl, brlShort, periodLabel } from "@/lib/contas/format";
import { availablePeriods, findState, panelHref, readFederalState } from "@/lib/contas/state";
import type { ContasExecution, ContasLens, ContasMeta, ContasSearch, ContasTable, ExecutionRow } from "@/lib/contas/types";
import { useAsync } from "@/lib/useAsync";

export const EXECUTION_PHASES = ["committed", "liquidated", "paid", "payables_registered", "payables_cancelled", "payables_paid"] as const satisfies readonly (keyof ExecutionRow)[];

/** Trocar a lente inicia um recorte próprio: filtros de uma fonte não migram para outra. */
export function ContasLensNav({ meta, lens }: { meta: ContasMeta; lens: ContasLens }) {
  const t = useTranslations("contas.federal");
  return <nav className="contas-lens-nav" aria-label={t("lenses")}>
    {meta.lenses.map((item) => <Link key={item.lens} href={`/contas/painel?lens=${item.lens}`} aria-current={item.lens === lens ? "page" : undefined}>{t(item.lens)}</Link>)}
  </nav>;
}

/** B usa sede cadastral. C expõe somente as fases e dimensões que já existem na Gold. */
export function FederalDashboard({ meta, lens, onRetry }: { meta: ContasMeta; lens: "B" | "C"; onRetry: () => void }) {
  const t = useTranslations("contas.federal");
  const c = useTranslations("contas");
  const search = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const state = readFederalState(new URLSearchParams(search), meta, lens);
  const { group, period, page, filters, geography } = state;
  const definition = meta.lenses.find((item) => item.lens === lens);
  const groups = (definition?.group_by ?? []).filter((g) => g.id !== "territory" || !geography.startsWith("municipio:"));
  const filterKey = JSON.stringify(filters);
  const change = (values: Record<string, string | number>, nextFilters = filters) => {
    const next = new URLSearchParams(search);
    next.set("lens", lens);
    for (const [key, value] of Object.entries(values)) next.set(key, String(value));
    next.delete("filter");
    nextFilters.forEach((filter) => next.append("filter", filter));
    router.push(`${path}?${next}`, { scroll: false });
  };
  const loaded = useAsync(async () => {
    if (lens === "C") {
      const execution = await contasApi.execution({ periods: [period], dimension: group, filter: filters, page });
      if (execution.provenance.release_id !== meta.release_id) throw new Error("release_changed");
      return { execution, receipts: null, series: null, territory: null, scope: state };
    }
    const selected = await api.geography(geography);
    const parent = selected.level_id === "municipio" ? await findState(selected, api.geography) : null;
    const within = selected.level_id === "uf" ? geography : parent?.geography_key ?? null;
    if (selected.level_id === "municipio" && !within) throw new Error("territory_unavailable");
    const level = within ? "municipio" as const : "uf" as const;
    const [receipts, series, states, map, collection] = await Promise.all([
      contasApi.table({ lens, geography_key: geography, periods: [period], group_by: group, filter: filters, page }),
      // A série é do território inteiro; o título e a nota deixam esse universo explícito.
      contasApi.series({ lens, geography_key: geography, periods: [period], grain: "mes" }),
      api.geographies("uf"),
      contasApi.map({ lens, level, within, periods: [period] }),
      api.geometry(level, within),
    ]);
    const municipalities = within ? collection.features.map((f) => ({ geography_key: f.id, name: f.properties.name })).sort((a, b) => a.name.localeCompare(b.name, "pt-BR")) : [];
    if ([receipts, series, map].some((r) => r.provenance.release_id !== meta.release_id)) throw new Error("release_changed");
    return { execution: null, receipts, series, territory: { selected, parent, within, states, municipalities, map, collection }, scope: state };
  }, [lens, group, period, page, filterKey, geography, meta.release_id]);
  const data = loaded.data;
  const result = data?.execution ?? data?.receipts;
  const [hover, setHover] = useState<{ key: string; name: string; x: number; y: number } | null>(null);
  const hovered = data?.territory?.map.rows.find((row) => row.geography_key === hover?.key);
  const jumped = useRef(false);
  useEffect(() => {
    if (!data || jumped.current) return;
    jumped.current = true;
    if (/^#fase-(committed|liquidated|paid|payables_registered|payables_cancelled|payables_paid)$/.test(window.location.hash)) {
      document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "center" });
    }
  }, [data]);
  const profileHref = (id: string) => `/contas/favorecidos/${encodeURIComponent(id)}?${new URLSearchParams({ year: period.slice(0, 4), back: panelHref(new URLSearchParams(search)) })}`;
  const addFilter = (code: string) => {
    if (!definition?.dimensions.some((d) => d.id === group)) return;
    change({ page: 1 }, [...filters.filter((f) => !f.startsWith(`${group}:`)), `${group}:${code}`]);
  };
  const groupLabel = groups.find((g) => g.id === group)?.label ?? group;
  return <div className="dashboard contas-dashboard">
    <aside className="sidebar contas-sidebar">
      <div className="sb-current"><p className="sb-crumb">{c("blockName")}</p><p className="sb-kpi">{t(lens)}</p></div>
      <section className="filters" aria-label={c("filters")}><h2>{c("filters")}</h2><div className="filters-body">
        {lens === "B" ? <>
          <label className="field">{t("territory")}<select value={data?.territory?.within ?? "brasil:1"} onChange={(e) => change({ geography: e.target.value, page: 1 })}>
            <option value="brasil:1">{c("brasil")}</option>{data?.territory?.states.map((g) => <option key={g.geography_key} value={g.geography_key}>{g.name}</option>)}
          </select></label>
          {data?.territory?.within ? <label className="field">{t("municipality")}<select value={geography} onChange={(e) => change({ geography: e.target.value, page: 1 })}>
            <option value={data.territory.within}>{t("allMunicipalities")}</option>{data.territory.municipalities.map((g) => <option key={g.geography_key} value={g.geography_key}>{g.name}</option>)}
          </select></label> : null}
        </> : null}
        <label className="field">{c("period")}<select value={period} onChange={(e) => change({ period: e.target.value, page: 1 })}>{availablePeriods(meta, lens).map((p) => <option key={p} value={p}>{periodLabel(p)}</option>)}</select></label>
        <label className="field">{t("group")}<select value={group} onChange={(e) => change({ group: e.target.value, page: 1 })}>{groups.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}</select></label>
      </div><div className="filters-foot"><button className="clear" type="button" onClick={() => router.push(`${path}?lens=${lens}`, { scroll: false })}>{t("clear")}</button></div></section>
    </aside>
    <main className="main contas-content contas-federal" aria-busy={loaded.loading}>
      <header><p className="crumb">{c("blockName")}</p><h1>{t(lens)} · {periodLabel(period)}{data?.territory ? ` · ${data.territory.selected.name}` : ""}</h1></header>
      <p className="card contas-lens-note">{t(lens === "C" ? "noGeography" : "receiptsNote")}</p>
      {lens === "C" ? <p>{t("noSum")}</p> : null}
      {filters.length ? <section aria-label={t("filters")} className="contas-active-filters">{filters.map((f) => <button className="btn-outline" key={f} type="button" aria-label={t("remove", { label: f })} onClick={() => change({ page: 1 }, filters.filter((other) => other !== f))}>{definition?.dimensions.find((d) => d.id === f.split(":")[0])?.label}: {f.slice(f.indexOf(":") + 1)} ×</button>)}</section> : null}
      {loaded.loading ? <p role="status">{c("loading")}</p> : !data || !result ? <ContasUnavailable onRetry={onRetry} /> : <>
        <PeriodStatusList provenance={result.provenance} />
        {data.execution ? <ul className="contas-highlights contas-phase-cards">{EXECUTION_PHASES.map((phase) => <li className="contas-kpi" key={phase} id={`fase-${phase}`} data-phase={phase}><span className="contas-kpi-label">{t(`phases.${phase}`)}</span><span className="contas-kpi-value">{brlShort(data.execution.total[phase])}</span><span className="contas-kpi-note">{brl(data.execution.total[phase])}</span></li>)}</ul> : <div className="card contas-kpi"><span className="contas-kpi-label">{t("total")}</span><strong className="contas-kpi-value">{brl(data.receipts!.value_total)}</strong></div>}
        <section className="card contas-section" aria-labelledby="federal-table"><h2 id="federal-table">{t("table")} · {groupLabel}</h2><p>{t(lens === "C" || definition?.dimensions.some((d) => d.id === group) ? "filterHint" : "tableProfileHint")}</p><p>{t("ordered")}</p>
          {data.execution ? <ExecutionTable result={data.execution} onFilter={addFilter} /> : <ReceiptsTable result={data.receipts!} groupLabel={groupLabel} onFilter={definition?.dimensions.some((d) => d.id === group) ? addFilter : undefined} profileHref={profileHref} />}
          {!result.rows.length ? <p>{t(result.rows_total ? "emptyPage" : "empty")}</p> : null}
          <p>{t("count", { count: result.rows_total })}</p>
          {result.rows_total > result.pages * result.page_size ? <p>{t("limit")}</p> : null}
          <div className="contas-pager"><button type="button" aria-label={t("previous")} disabled={result.page <= 1} onClick={() => change({ page: Math.max(1, Math.min(page - 1, result.pages)) })}>‹</button><span>{t("page", { page: result.page, pages: Math.max(1, result.pages) })}</span><button type="button" aria-label={t("next")} disabled={result.pages === 0 || result.page >= result.pages} onClick={() => change({ page: page + 1 })}>›</button></div>
        </section>
        {data.territory ? <section className="card contas-section" aria-labelledby="federal-map"><h2 id="federal-map">{t("seatMap")}</h2><p>{t("territoryScope")}</p><div className="contas-map-wrap"><MapView groupedControls context={null} onHover={(key, name, event) => setHover(key ? { key, name, x: event.clientX, y: event.clientY } : null)} collection={data.territory.collection} values={toMapValues(data.territory.map)} selected={geography} focus={data.territory.within} fitRequest={{ key: data.territory.within, n: 0 }} canUp={geography !== "brasil:1"} onSelect={(key) => change({ geography: key, page: 1 })} onDrill={(key) => { change({ geography: key, page: 1 }); return true; }} onUp={() => change({ geography: data.territory?.parent?.geography_key ?? "brasil:1", page: 1 })} onReset={() => change({ geography: "brasil:1", page: 1 })} label={t("seatMap")} legendTitle={t("amount")} /></div></section> : null}
        {hover && hovered ? <div className="contas-tooltip-position" style={{ left: Math.max(8, Math.min(hover.x + 12, window.innerWidth - 320)), top: Math.max(8, Math.min(hover.y + 12, window.innerHeight - 240)) }}><ContasTooltip lensLabel={t("B")} name={hover.name} value={hovered.value} period={periodLabel(period)} inline /></div> : null}
        {data.series ? <section className="card contas-section" aria-labelledby="federal-series"><h2 id="federal-series">{t("series")}</h2><p>{t("territoryScope")}</p><div className="contas-series-wrap"><SeriesChart data={toSeries(data.series, data.territory?.selected.name ?? c("brasil"))} /></div></section> : null}
        {lens === "B" ? <RecipientSearch release={meta.release_id} profileHref={profileHref} /> : null}
        <section className="card contas-section"><p>{t("source")} · {t("release")} <code>{result.provenance.release_id.slice(0, 8)}</code></p>{definition?.notes.map((note) => <p key={note}>{note}</p>)}<ContasReferences /></section>
      </>}
    </main>
  </div>;
}

function ExecutionTable({ result, onFilter }: { result: ContasExecution; onFilter: (code: string) => void }) {
  const t = useTranslations("contas.federal");
  return <div className="table-wrap contas-execution-wrap" tabIndex={0} role="region" aria-label={t("table")}><table className="data-table contas-execution-table"><caption className="sr-only">{t("C")}</caption><thead><tr><th scope="col">{t("category")}</th>{EXECUTION_PHASES.map((phase) => <th className="num" key={phase} scope="col">{t(`phases.${phase}`)}</th>)}</tr></thead><tbody>{result.rows.map((row) => <tr key={row.category_code}><th scope="row"><button type="button" className="text-btn" onClick={() => onFilter(row.category_code)}>{row.label}</button></th>{EXECUTION_PHASES.map((phase) => <td className="num" key={phase}>{brl(row[phase])}</td>)}</tr>)}</tbody><tfoot><tr><th scope="row">{t("totalRow")}</th>{EXECUTION_PHASES.map((phase) => <td className="num" key={phase}>{brl(result.total[phase])}</td>)}</tr></tfoot></table></div>;
}

function ReceiptsTable({ result, groupLabel, onFilter, profileHref }: { result: ContasTable; groupLabel: string; onFilter?: (code: string) => void; profileHref: (id: string) => string }) {
  const t = useTranslations("contas.federal");
  return <div className="table-wrap"><table className="data-table"><caption className="sr-only">{t("B")}</caption><thead><tr><th scope="col">{groupLabel}</th><th className="num" scope="col">{t("amount")}</th></tr></thead><tbody>{result.rows.map((row) => <tr key={row.key}><th scope="row">{row.recipient ? <Link href={profileHref(row.recipient.recipient_id)}>{row.recipient.name ?? row.label}</Link> : onFilter ? <button className="text-btn" type="button" onClick={() => onFilter(row.key)}>{row.label}</button> : row.label}</th><td className="num">{brl(row.value)}</td></tr>)}</tbody><tfoot><tr><th scope="row">{t("totalRow")}</th><td className="num">{brl(result.value_total)}</td></tr></tfoot></table></div>;
}

function RecipientSearch({ release, profileHref }: { release: string; profileHref: (id: string) => string }) {
  const t = useTranslations("contas.federal");
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [retry, setRetry] = useState(0);
  const result = useAsync<ContasSearch>(submitted ? async () => {
    const response = await contasApi.search(submitted);
    if (response.release_id !== release) throw new Error("release_changed");
    return response;
  } : null, [submitted, release], retry);
  const submit = (event: FormEvent) => { event.preventDefault(); setSubmitted(query.trim()); setRetry((n) => n + 1); };
  return <section className="card contas-section"><form onSubmit={submit}><label className="field">{t("search")}<input type="search" minLength={3} maxLength={80} required value={query} onChange={(event) => setQuery(event.target.value)} /></label><button type="submit" className="btn-outline" disabled={result.loading}>{t("searchButton")}</button></form><p>{t("searchHint")}</p><div aria-live="polite">{result.loading ? <p>{t("searching")}</p> : result.error ? <p role="alert">{t("searchError")}</p> : result.data ? <ul>{result.data.hits.filter((hit) => hit.kind === "favorecido").map((hit) => <li key={hit.id}><Link href={profileHref(hit.id)}>{hit.label}</Link></li>)}{!result.data.hits.some((hit) => hit.kind === "favorecido") ? <li>{t("noSearch")}</li> : null}</ul> : null}</div></section>;
}
