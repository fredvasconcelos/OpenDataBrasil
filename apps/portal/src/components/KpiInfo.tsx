"use client";

import { useTranslations } from "next-intl";

import type { Kpi } from "@/lib/types";

// Metadados visíveis do indicador (§19.4) em formato de rodapé: fonte, unidade,
// períodos, licença e versão numa linha; descrição e limitações sob demanda.
export function KpiInfo({ kpi, releaseId }: { kpi: Kpi; releaseId: string }) {
  const t = useTranslations("meta");
  const periods = kpi.periods.length > 1 ? `${kpi.periods[0]}–${kpi.periods.at(-1)}` : kpi.periods[0];
  return (
    <footer className="kpi-footer small" aria-label={t("title")}>
      <span>
        {t("source")}: IBGE · {t("table", { table: kpi.source.source_table_id, variable: kpi.source.source_variable_id })}
        {kpi.source.reference_url ? (
          <>
            {" "}
            (
            <a href={kpi.source.reference_url} target="_blank" rel="noreferrer">
              {t("official")}
            </a>
            )
          </>
        ) : null}
      </span>
      <span>
        {t("unit")}: {kpi.unit}
      </span>
      <span>
        {t("periods")}: {periods}
      </span>
      <span>
        {t("license")}: {kpi.source.license_id ?? "—"}
      </span>
      <span>
        {t("release")}: <code title={releaseId}>{releaseId.slice(0, 8)}</code>
      </span>
      <details>
        <summary>{kpi.caveats.length ? t("moreWithCaveats", { count: kpi.caveats.length }) : t("more")}</summary>
        <div className="kpi-more card">
          <p>{kpi.description}</p>
          {kpi.caveats.length ? (
            <>
              <h3>{t("caveats")}</h3>
              <ul>
                {kpi.caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      </details>
    </footer>
  );
}
