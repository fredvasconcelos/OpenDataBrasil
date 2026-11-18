"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { AccessRanking } from "@/components/AccessRanking";
import { AccessTable } from "@/components/AccessTable";
import { AccessTooltip } from "@/components/AccessTooltip";
import { MetricsPeriod } from "@/components/MetricsPeriod";
import { TopDatasets } from "@/components/TopDatasets";
import { api } from "@/lib/api";
import { rewindForD3 } from "@/lib/geo";
import {
  buildRankingTree,
  formatCount,
  formatRange,
  REGIONS,
  regionOfUf,
  type DatasetSort,
  type DatasetsResponse,
  type GeoItem,
  type GeoLevel,
  type MetricsSummary,
  type PeriodRequest,
} from "@/lib/metrics";
import type { GeoCollection } from "@/lib/types";

// O mapa só no navegador (d3-geo, globo e bandeiras), com o esqueleto até carregar.
const AccessMap = dynamic(() => import("@/components/AccessMap").then((m) => m.AccessMap), {
  ssr: false,
  loading: () => <div className="access-map-loading skeleton" aria-hidden="true" />,
});

type Loaded =
  | { key: string; status: "ok"; summary: MetricsSummary; countries: GeoItem[]; regions: GeoItem[]; ufs: GeoItem[] }
  | { key: string; status: "empty" }
  | { key: string; status: "error" };

const LEVELS: readonly GeoLevel[] = ["pais", "regiao", "uf"];
const dateFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeZone: "America/Sao_Paulo" });

// Página Métricas (DS 2.12, ADR-0027): número de acessos com fonte e período, mapa em três
// níveis (País › Grande Região › Estado), ranking em árvore, o mapa como tabela e os
// indicadores mais acessados. Sem cookies: só visualizações, nunca "visitantes".
// Antes de a coleta existir, a API responde 404 e a página diz que a coleta não começou;
// nenhum número é estimado nem inventado (fixtures só nos testes).
export function MetricsView() {
  const t = useTranslations("metrics");
  const [period, setPeriod] = useState<PeriodRequest>({ period: "30d" });
  const [level, setLevel] = useState<GeoLevel>("pais");
  const [within, setWithin] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [asTable, setAsTable] = useState(false);
  const [sort, setSort] = useState<DatasetSort>("views");
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [datasets, setDatasets] = useState<{ key: string; data: DatasetsResponse | null } | null>(null);
  const [geometry, setGeometry] = useState<{ regions: GeoCollection; ufs: GeoCollection } | null>(null);

  const periodKey = JSON.stringify(period);
  const datasetsKey = `${periodKey}|${sort}`;

  useEffect(() => {
    let alive = true;
    Promise.all([
      api.metricsSummary(period),
      api.metricsGeo("pais", null, period),
      api.metricsGeo("regiao", "pais:BR", period),
      api.metricsGeo("uf", "pais:BR", period),
    ])
      .then(([summary, countries, regions, ufs]) => {
        if (!alive) return;
        setLoaded(
          summary
            ? { key: periodKey, status: "ok", summary, countries: countries?.items ?? [], regions: regions?.items ?? [], ufs: ufs?.items ?? [] }
            : { key: periodKey, status: "empty" },
        );
      })
      .catch(() => {
        if (alive) setLoaded({ key: periodKey, status: "error" });
      });
    return () => {
      alive = false;
    };
  }, [period, periodKey]);

  useEffect(() => {
    let alive = true;
    api
      .metricsDatasets(sort, period)
      .then((data) => {
        if (alive) setDatasets({ key: datasetsKey, data });
      })
      .catch(() => {
        if (alive) setDatasets({ key: datasetsKey, data: null });
      });
    return () => {
      alive = false;
    };
  }, [sort, period, datasetsKey]);

  // Geometria das Grandes Regiões e das UFs (do release), só quando o mapa sai do globo.
  const needsBrazil = level !== "pais";
  useEffect(() => {
    if (!needsBrazil || geometry) return;
    let alive = true;
    Promise.all([api.geometry("regiao"), api.geometry("uf")])
      .then(([regions, ufs]) => {
        // Mesmo cuidado do MapView: anéis no sentido que o d3-geo espera.
        if (alive) setGeometry({ regions: rewindForD3(regions), ufs: rewindForD3(ufs) });
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [needsBrazil, geometry]);

  const ok = loaded && loaded.key === periodKey && loaded.status === "ok" ? loaded : null;
  const tree = useMemo(() => (ok ? buildRankingTree(ok.countries, ok.regions, ok.ufs) : []), [ok]);
  const items = useMemo<GeoItem[]>(() => {
    if (!ok) return [];
    if (level === "pais") return ok.countries;
    if (level === "regiao") return ok.regions;
    return within?.startsWith("regiao:") ? ok.ufs.filter((u) => regionOfUf(u.geography_key) === within) : ok.ufs;
  }, [ok, level, within]);
  const allItems = useMemo(() => (ok ? [...ok.countries, ...ok.regions, ...ok.ufs] : []), [ok]);
  const chosen = selected ? allItems.find((i) => i.geography_key === selected) : undefined;
  const range = ok ? formatRange(ok.summary.period) : "";

  // Leva o mapa até o lugar (clique no mapa, no ranking ou na tabela).
  const go = (key: string) => {
    if (key === "pais:BR") {
      setLevel("regiao");
      setWithin("pais:BR");
      setSelected(key);
    } else if (key.startsWith("pais:")) {
      setLevel("pais");
      setWithin(null);
      setSelected(key);
    } else if (key.startsWith("regiao:")) {
      setLevel("uf");
      setWithin(key);
      setSelected(key);
    } else if (key.startsWith("uf:")) {
      setLevel("uf");
      setWithin(regionOfUf(key));
      setSelected(key);
    }
  };
  const chooseLevel = (l: GeoLevel) => {
    setLevel(l);
    setWithin(l === "pais" ? null : "pais:BR");
  };

  const status = !loaded || loaded.key !== periodKey ? "loading" : loaded.status;
  const regionName = within?.startsWith("regiao:") ? REGIONS[within]?.name : null;

  return (
    <main className="page page-wide metrics-page">
      <section className="page-intro">
        <h1>{t("title")}</h1>
        <p className="lead">{t("lead")}</p>
      </section>
      <MetricsPeriod value={period} onChange={setPeriod} />

      {status === "loading" ? (
        <div className="card metrics-block" aria-busy="true">
          <span className="skeleton" />
          <span className="skeleton short" />
        </div>
      ) : null}
      {status === "error" ? (
        <p className="card metrics-block metrics-error" role="alert">
          {t("error")}
        </p>
      ) : null}
      {status === "empty" ? (
        <section className="card metrics-block metrics-empty" aria-labelledby="metricas-vazio">
          <h2 id="metricas-vazio">{t("empty.title")}</h2>
          <p>{t("empty.text")}</p>
        </section>
      ) : null}

      {ok ? (
        <>
          <section className="card metrics-block metrics-summary" aria-labelledby="metricas-total">
            <h2 id="metricas-total">{t("total")}</h2>
            <p className="metrics-total">
              <span className="metrics-total-value">{formatCount(ok.summary.views)}</span> <span className="metrics-total-unit">{t("totalUnit")}</span>
            </p>
            <p className="muted metrics-period-line">
              {t("source", { range })}
              {ok.summary.collection_started_at
                ? ` · ${t("since", { date: dateFmt.format(new Date(ok.summary.collection_started_at)) })}`
                : ""}
            </p>
            <dl className="metrics-cards">
              <div>
                <dt>{t("cards.kpiOpens")}</dt>
                <dd>{formatCount(ok.summary.kpi_opens)}</dd>
              </div>
              <div>
                <dt>{t("cards.downloads")}</dt>
                <dd>{formatCount(ok.summary.downloads)}</dd>
              </div>
              <div>
                <dt>{t("cards.countries")}</dt>
                <dd>{formatCount(ok.summary.countries)}</dd>
              </div>
              {ok.summary.api_calls !== null ? (
                <div>
                  <dt>{t("cards.apiCalls")}</dt>
                  <dd>{formatCount(ok.summary.api_calls)}</dd>
                </div>
              ) : null}
            </dl>
          </section>

          <section className="card metrics-block" aria-labelledby="metricas-mapa">
            <div className="metrics-block-head">
              <h2 id="metricas-mapa">{t("map.title")}</h2>
              <div className="segmented" role="group" aria-label={t("map.level")}>
                {LEVELS.map((l) => (
                  <button key={l} type="button" aria-pressed={level === l} onClick={() => chooseLevel(l)}>
                    {t(`map.levels.${l}`)}
                  </button>
                ))}
              </div>
            </div>
            <nav className="metrics-trail" aria-label={t("map.trail")}>
              <button type="button" className="link-btn" onClick={() => chooseLevel("pais")} aria-current={level === "pais" ? "page" : undefined}>
                {t("map.world")}
              </button>
              {level !== "pais" ? (
                <>
                  <span aria-hidden="true"> › </span>
                  <button type="button" className="link-btn" onClick={() => chooseLevel("regiao")} aria-current={!regionName ? "page" : undefined}>
                    {t("map.brazil")}
                  </button>
                </>
              ) : null}
              {regionName ? (
                <>
                  <span aria-hidden="true"> › </span>
                  <span aria-current="page">{regionName}</span>
                </>
              ) : null}
            </nav>
            <p className="muted metrics-hint">{level === "pais" ? t("map.globeHint") : t("map.brazilHint")}</p>
            {items.length ? (
              asTable ? (
                <AccessTable items={items} levelLabel={t(`map.levels.${level}`)} selected={selected} onSelect={go} />
              ) : (
                <AccessMap
                  level={level}
                  items={items}
                  regions={geometry?.regions ?? null}
                  ufs={geometry?.ufs ?? null}
                  within={within}
                  selected={selected}
                  period={range}
                  onActivate={go}
                />
              )
            ) : (
              <p className="empty">{t("map.empty")}</p>
            )}
            <button type="button" className="btn-outline metrics-toggle" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
              {asTable ? t("map.asMap") : t("map.asTable")}
            </button>
            {chosen ? <AccessTooltip variant="card" item={chosen} period={range} onClose={() => setSelected(null)} /> : null}
          </section>

          <section className="card metrics-block" aria-labelledby="metricas-ranking">
            <h2 id="metricas-ranking">{t("ranking.title")}</h2>
            <p className="muted metrics-hint">{t("ranking.hint")}</p>
            <AccessRanking nodes={tree} selected={selected} onSelect={go} />
          </section>

          {datasets && datasets.key === datasetsKey && datasets.data ? (
            <TopDatasets items={datasets.data.items} sort={sort} onSort={setSort} period={range} />
          ) : null}
        </>
      ) : null}

      <section className="metrics-how" aria-labelledby="metricas-como">
        <h2 id="metricas-como">{t("how.title")}</h2>
        <p>{t("how.text")}</p>
      </section>
    </main>
  );
}
