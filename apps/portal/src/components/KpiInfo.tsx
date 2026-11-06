"use client";

import { useTranslations } from "next-intl";

import type { Kpi } from "@/lib/types";

// Metadados visíveis do indicador (§19.4): fonte, unidade, cobertura, limitações e versão.
export function KpiInfo({ kpi, releaseId }: { kpi: Kpi; releaseId: string }) {
  const t = useTranslations("meta");
  const periods = kpi.periods.length > 1 ? `${kpi.periods[0]}–${kpi.periods.at(-1)} (${kpi.periods.length})` : kpi.periods[0];
  return (
    <section className="card meta" aria-labelledby="meta-title">
      <h2 id="meta-title" style={{ fontSize: 15, marginTop: 0 }}>
        {t("title")}
      </h2>
      <p style={{ marginTop: 0 }}>{kpi.description}</p>
      <dl>
        <dt>{t("source")}</dt>
        <dd>
          IBGE · {t("table", { table: kpi.source.source_table_id, variable: kpi.source.source_variable_id })}
          {kpi.source.reference_url ? (
            <>
              {" "}
              ·{" "}
              <a href={kpi.source.reference_url} target="_blank" rel="noreferrer">
                {t("official")}
              </a>
            </>
          ) : null}
        </dd>
        <dt>{t("unit")}</dt>
        <dd>{kpi.unit}</dd>
        <dt>{t("periods")}</dt>
        <dd>{periods}</dd>
        <dt>{t("license")}</dt>
        <dd>{kpi.source.license_id}</dd>
        <dt>{t("release")}</dt>
        <dd>
          <code>{releaseId}</code>
        </dd>
      </dl>
      {kpi.caveats.length ? (
        <>
          <h3 style={{ fontSize: 13, marginBottom: 4 }}>{t("caveats")}</h3>
          <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
            {kpi.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
