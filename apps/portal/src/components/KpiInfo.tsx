"use client";

import { useTranslations } from "next-intl";

import type { Kpi } from "@/lib/types";
import { useMediaQuery, WIDE_QUERY } from "@/lib/useMediaQuery";
import { formatPeriod } from "@/lib/format";

// Metadados visíveis do indicador (§19.4). Design System ODBr:
// - a linha da fonte (fonte, tabela, link oficial, licença, release) fica sempre visível;
// - descrição, unidade, períodos e limitações ficam em "Sobre este indicador".
// Na tela cheia (≥ 1600 px) o bloco vira o rodapé do painel e começa fechado;
// nas telas menores começa aberto, como cartão no fim da página.
export function KpiInfo({ kpi, releaseId }: { kpi: Kpi; releaseId: string }) {
  const t = useTranslations("meta");
  const wide = useMediaQuery(WIDE_QUERY);
  const periods =
    kpi.periods.length > 1
      ? `${formatPeriod(kpi.periods[0] ?? "")}–${formatPeriod(kpi.periods.at(-1) ?? "")} (${kpi.periods.length})`
      : formatPeriod(kpi.periods[0] ?? "");
  return (
    <section className="card meta" aria-labelledby="meta-title">
      <h2 id="meta-title" className="sr-only">
        {t("title")}
      </h2>
      <p className="meta-source">
        <strong>{t("source")}:</strong> {kpi.source.institution ?? "IBGE"} ·{" "}
        {/* SIDRA: "Tabela SIDRA N"; outras fontes (ex.: Sinesp VDE): o identificador da tabela. */}
        {t(kpi.source.system === "SIDRA" || !kpi.source.institution ? "table" : "tableOther", {
          table: kpi.source.source_table_id,
          variable: kpi.source.source_variable_id,
        })}
        {kpi.source.reference_url ? (
          <>
            {" · "}
            <a href={kpi.source.reference_url} target="_blank" rel="noreferrer">
              {t("official")}
            </a>
          </>
        ) : null}
        {" · "}
        {t("license")} {kpi.source.license_id}
        {" · "}
        {t("release")} <code>{releaseId.slice(0, 8)}</code>
      </p>
      <details key={wide ? "wide" : "narrow"} className="meta-more" open={!wide}>
        <summary>
          {t("title")}
          {kpi.caveats.length ? ` · ${t("caveats")} (${kpi.caveats.length})` : ""}
        </summary>
        <p>{kpi.description}</p>
        <dl>
          <dt>{t("unit")}</dt>
          <dd>{kpi.unit}</dd>
          <dt>{t("periods")}</dt>
          <dd>{periods}</dd>
          <dt>{t("release")}</dt>
          <dd>
            <code>{releaseId}</code>
          </dd>
        </dl>
        {kpi.caveats.length ? (
          <>
            <h3>{t("caveats")}</h3>
            <ul className="small">
              {kpi.caveats.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </>
        ) : null}
      </details>
    </section>
  );
}
