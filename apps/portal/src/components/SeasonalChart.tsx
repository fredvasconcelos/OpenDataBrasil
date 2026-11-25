"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { CoverageIcon } from "@/components/icons";
import { SeasonPlot, type SeasonBar, partLabel } from "@/components/SeasonChart";
import { formatPeriod, formatValue } from "@/lib/format";
import type { Seasonal } from "@/lib/types";

/** Uma barra por parte e série; valores e severidades vêm da API (ADR-0041). */
export function SeasonalChart({ data }: { data: Seasonal }) {
  const t = useTranslations("dashboard");
  const [open, setOpen] = useState(false);
  const previous = useRef("");
  const deepest = Math.max(0, ...data.series.map((s) => s.depth));
  const shown = deepest ? data.series.filter((s) => s.depth === deepest) : data.series;
  const labels = shown.map((s) => s.label);
  const parts = data.series[0]?.points.map((p) => p.part) ?? [];
  const bars: SeasonBar[] = parts.map((part) => {
    const points = shown.map((s) => s.points.find((p) => p.part === part)!);
    return { part, values: points.map((p) => p.value), statuses: points.map((p) => p.status),
      coverage: points.map((p) => ({ present: p.present, expected: p.expected })) };
  });
  const alerts = shown.flatMap((s) => s.points.filter((p) => p.severity)
    .map((p) => ({ ...p, label: s.label })));
  const severity = alerts.some((p) => p.severity === "danger") ? "danger" : alerts.length ? "warning" : null;
  const signature = JSON.stringify([data.kpi_id, data.geography.geography_key, data.year_from, data.year_to, alerts]);
  useEffect(() => {
    if (signature !== previous.current) {
      previous.current = signature;
      setOpen(severity === "danger");
    }
  }, [signature, severity]);
  const how = t("seasonalSum", { from: data.year_from, to: data.year_to });
  return <div className="seasonal-result">
    <SeasonPlot bars={bars} labels={labels} how={how} unit={data.unit} />
    {severity ? <div className={`seasonal-alerts is-${severity}`}>
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
        <CoverageIcon severity={severity} /> {t(`seasonalRisk.${severity}`)}
      </button>
      {open ? <ul>{alerts.map((p) => <li key={`${p.label}|${p.part}`}>
        <strong>{p.part === "ano" ? t("seasonalYear") : partLabel(p.part)} · {p.label}: </strong>
        {t(p.blocked.length ? "seasonalBlocked" : p.present ? "seasonalCoverage" : "seasonalEmpty",
          { present: p.present, expected: p.expected })}
        {p.missing.length ? <span> {t("seasonalMissing", { periods: p.missing.map(formatPeriod).join(", ") })}</span> : null}
        {p.blocked.length ? <span> {t("seasonalBlockedParts", { periods: p.blocked.map(formatPeriod).join(", ") })}</span> : null}
        {p.input_partial.length ? <span> {t("seasonalInputPartial")}</span> : null}
      </li>)}</ul> : null}
    </div> : null}
    <p className="small muted">{t("seasonalScope")}</p>
    <details className="seasonal-notes"><summary>{t("seasonalValues")}</summary>
      <ul>{shown.flatMap((s) => s.points.map((p) => <li key={`${s.key}|${p.part}`}>
        {p.part === "ano" ? t("seasonalYear") : partLabel(p.part)} · {s.label}: {formatValue(p.value, p.status)}. {t("seasonalCoverage", { present: p.present, expected: p.expected })}
      </li>))}</ul>
    </details>
    {data.notes.length ? <details className="seasonal-notes"><summary>{t("seasonalNotes")}</summary>
      <ul>{data.notes.map((note, i) => <li key={i}>{note}</li>)}</ul>
    </details> : null}
  </div>;
}
