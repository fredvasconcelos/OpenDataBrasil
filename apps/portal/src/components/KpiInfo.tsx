"use client";

import { useTranslations } from "next-intl";

import { useRef } from "react";

import { allSourceTables, tablesInUse } from "@/lib/source-tables";
import type { Kpi } from "@/lib/types";
import { useMediaQuery, WIDE_QUERY } from "@/lib/useMediaQuery";
import { formatPeriod } from "@/lib/format";

// Metadados visíveis do indicador (§19.4). Design System ODBr:
// - a linha da fonte (fonte, tabela, link oficial, licença, release) fica sempre visível;
// - descrição, unidade, períodos, método e limitações ficam em "Sobre este indicador".
// - "Método" (DS 2.3.10): como os valores derivados são calculados (correção por índice de
//   preços, agregação no tempo); a correção em uso aparece primeiro.
// - Tabelas de origem (DS 2.9): com um detalhe de tabela-irmã ativo, a linha da fonte cita
//   as tabelas em uso, cada uma com o link oficial ("4487 (Total) e 4490 (Cor ou raça)");
//   sem detalhe, a principal e um botão "N tabelas de origem", que abre a lista completa.
// Na tela cheia (≥ 1600 px) o bloco vira o rodapé do painel e começa fechado;
// nas telas menores começa aberto, como cartão no fim da página.
export function KpiInfo({
  kpi,
  releaseId,
  correction = null,
  dimensions = [],
}: {
  kpi: Kpi;
  releaseId: string;
  correction?: string | null;
  /** Detalhes ativos em "Detalhar por": escolhem as tabelas citadas na linha da fonte. */
  dimensions?: string[];
}) {
  const t = useTranslations("meta");
  const more = useRef<HTMLDetailsElement>(null);
  const inUse = tablesInUse(kpi, dimensions, t("tableTotal"));
  const all = allSourceTables(kpi, t("tableTotal"));
  const sidra = kpi.source.system === "SIDRA" || !kpi.source.institution;
  const openTables = () => {
    if (more.current) more.current.open = true;
    document.getElementById("tabelas-origem")?.scrollIntoView({ block: "nearest" });
  };
  const span = (periods: string[]) =>
    periods.length > 3
      ? `${formatPeriod(periods[0] ?? "")}–${formatPeriod(periods.at(-1) ?? "")}`
      : periods.map((p) => formatPeriod(p)).join(", ");
  const tg = useTranslations("grainNotes");
  const corrections = [...(kpi.corrections ?? [])].sort(
    (a, b) => Number(b.correction_id === correction) - Number(a.correction_id === correction),
  );
  const hasMethod = corrections.length > 0 || Boolean(kpi.time_aggregation);
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
        {inUse.length > 1 ? (
          <>
            {/* Detalhe de tabela-irmã ativo: as tabelas em uso, cada uma com o link oficial. */}
            {sidra ? t("tablesSidra") : t("tablesOther")}{" "}
            {inUse.map((tb, i) => (
              <span key={tb.id}>
                {i > 0 ? (i === inUse.length - 1 ? ` ${t("and")} ` : ", ") : null}
                {tb.url ? (
                  <a href={tb.url} target="_blank" rel="noreferrer" title={t("officialTable", { table: tb.id })}>
                    {tb.id}
                  </a>
                ) : (
                  tb.id
                )}{" "}
                ({tb.role.join(", ")})
              </span>
            ))}
            , {t("variable", { variable: kpi.source.source_variable_id })}
          </>
        ) : (
          <>
            {/* SIDRA: "Tabela SIDRA N"; outras fontes (ex.: Sinesp VDE): o identificador da tabela. */}
            {t(sidra ? "table" : "tableOther", {
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
            {all.length > 1 ? (
              <>
                {" · "}
                <button type="button" className="link-btn" aria-controls="tabelas-origem" onClick={openTables}>
                  {t("moreTables", { count: all.length })}
                </button>
              </>
            ) : null}
          </>
        )}
        {" · "}
        {t("license")} {kpi.source.license_id}
        {" · "}
        {t("release")} <code>{releaseId.slice(0, 8)}</code>
      </p>
      <details ref={more} key={wide ? "wide" : "narrow"} className="meta-more" open={!wide}>
        <summary>
          {t("title")}
          {hasMethod ? ` · ${t("method")}` : ""}
          {kpi.caveats.length ? ` · ${t("caveats")} (${kpi.caveats.length})` : ""}
        </summary>
        <div className="meta-body">
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
        {hasMethod ? (
          <>
            <h3 id="metodo">{t("method")}</h3>
            <ul className="small method-list">
              {corrections.map((c) => (
                <li key={c.correction_id}>
                  <strong>
                    {t("correctedBy", { label: c.label })}
                    {c.correction_id === correction ? ` ${t("inUse")}` : ""}:
                  </strong>{" "}
                  {c.note}
                </li>
              ))}
              {kpi.time_aggregation ? (
                <li>
                  <strong>{t("timeAggregation")}:</strong> {tg(kpi.time_aggregation)}
                </li>
              ) : null}
            </ul>
          </>
        ) : null}
        {all.length > 1 ? (
          <>
            <h3 id="tabelas-origem" tabIndex={-1}>
              {t("sourceTables")}
            </h3>
            <p className="small">{t("sourceTablesLead")}</p>
            <ul className="small source-tables">
              {all.map((tb) => (
                <li key={tb.id}>
                  <strong>
                    {tb.url ? (
                      <a href={tb.url} target="_blank" rel="noreferrer">
                        {sidra ? t("tableSidraShort", { table: tb.id }) : tb.id}
                      </a>
                    ) : sidra ? (
                      t("tableSidraShort", { table: tb.id })
                    ) : (
                      tb.id
                    )}
                  </strong>
                  {tb.role.length ? ` · ${tb.role.join(", ")}` : null}
                  {tb.periods.length ? ` · ${span(tb.periods)}` : null}
                </li>
              ))}
            </ul>
          </>
        ) : null}
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
        </div>
      </details>
    </section>
  );
}
