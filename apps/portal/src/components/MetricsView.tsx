"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { AccessRanking } from "@/components/AccessRanking";
import { AccessTooltip } from "@/components/AccessTooltip";
import { TopDatasets } from "@/components/TopDatasets";
import { api } from "@/lib/api";
import { rewindForD3 } from "@/lib/geo";
import {
  buildRankingTree,
  formatCount,
  formatRange,
  type DatasetsResponse,
  type GeoItem,
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

const period: PeriodRequest = { period: "all" };

// Página Métricas (DS 2.12, ADR-0027): número de acessos com fonte e período, mapa em três
// níveis (País › Estado por zoom), ranking geográfico em árvore e os
// indicadores mais acessados. Sem cookies: só visualizações, nunca "visitantes".
// Antes de a coleta existir, a API responde 404 e a página diz que a coleta não começou;
// nenhum número é estimado nem inventado (fixtures só nos testes).
export function MetricsView() {
  const t = useTranslations("metrics");
  const [selected, setSelected] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [datasets, setDatasets] = useState<{ key: string; data: DatasetsResponse | null } | null>(null);
  const [downloads, setDownloads] = useState<DatasetsResponse | null>(null);
  const [geometry, setGeometry] = useState<{ regions: GeoCollection; ufs: GeoCollection } | null>(null);

  const periodKey = JSON.stringify(period);
  const datasetsKey = periodKey;

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
  }, [periodKey]);

  useEffect(() => {
    let alive = true;
    api
      .metricsDatasets("views", period)
      .then((data) => {
        if (alive) setDatasets({ key: datasetsKey, data });
      })
      .catch(() => {
        if (alive) setDatasets({ key: datasetsKey, data: null });
      });
    api.metricsDatasets("downloads", period).then(data => { if (alive) setDownloads(data); }).catch(() => undefined);
    return () => { alive = false; };
  }, [datasetsKey]);

  // Carrega as geometrias do release para revelar UFs sem trocar de mapa.
  useEffect(() => {
    if (geometry) return;
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
  }, [geometry]);

  const ok = loaded && loaded.key === periodKey && loaded.status === "ok" ? loaded : null;
  const tree = useMemo(() => (ok ? buildRankingTree(ok.countries, ok.regions, ok.ufs) : []), [ok]);
  const allItems = useMemo(() => (ok ? [...ok.countries, ...ok.regions, ...ok.ufs] : []), [ok]);
  const chosen = selected && !selected.startsWith("regiao:") ? allItems.find((i) => i.geography_key === selected) : undefined;
  const range = ok ? formatRange(ok.summary.period) : "";

  // Leva o mapa até o lugar (clique no mapa, no ranking ou na tabela).
  const go = (key: string) => setSelected(key);
  const status = !loaded || loaded.key !== periodKey ? "loading" : loaded.status;

  return (
    <main className="page page-wide metrics-page">
      <section className="page-intro">
        <h1>{t("title")}</h1>
        <p className="lead">{t("lead")}</p>
      </section>

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
            <h2 id="metricas-total" className="sr-only">{t("total")}</h2>
            <dl className="metrics-cards">
              <div>
                <dt>{t("cards.views")}</dt>
                <dd>{formatCount(ok.summary.views)}</dd>
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

          <div className="metrics-layout">
          <section className="card metrics-block metrics-map-panel" aria-labelledby="metricas-mapa">
            <h2 id="metricas-mapa">{t("map.title")}</h2>
            <p className="muted metrics-hint">{t("map.globeHint")}</p>
            <AccessMap level="pais" items={ok.countries} stateItems={ok.ufs}
              regions={geometry?.regions ?? null} ufs={geometry?.ufs ?? null}
              within={null} selected={selected} period={range} onActivate={go} />
            {chosen ? <AccessTooltip variant="card" item={chosen} period={range} onClose={() => setSelected(null)} /> : null}
          </section>

          <aside className="metrics-rankings">
          <section className="card metrics-block" aria-labelledby="metricas-ranking">
            <h2 id="metricas-ranking">{t("ranking.title")}</h2>
            <p className="muted metrics-hint">{t("ranking.hint")}</p>
            <AccessRanking nodes={tree} selected={selected} onSelect={go} />
          </section>

          {datasets && datasets.key === datasetsKey && datasets.data ? (
            <TopDatasets items={datasets.data.items} sort="views" period={range} />
          ) : null}
          {downloads ? <TopDatasets items={downloads.items} sort="downloads" period={range} /> : null}
          </aside>
          </div>
        </>
      ) : null}

    </main>
  );
}
