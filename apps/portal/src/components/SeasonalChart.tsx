"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";

import { InfoIcon } from "@/components/icons";
import { SeasonPlot, type SeasonBar, partLabel } from "@/components/SeasonChart";
import { formatPeriod, formatValue } from "@/lib/format";
import type { Seasonal } from "@/lib/types";

/** Apresenta o acumulado e explica método/cobertura no botão i (ADR-0041). */
export function SeasonalChart({ data, heading }: { data: Seasonal; heading?: ReactNode }) {
  const t = useTranslations("dashboard");
  const [open, setOpen] = useState(false);
  const previous = useRef("");
  const head = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const infoId = useId();
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
  const signature = JSON.stringify([data.kpi_id, data.geography.geography_key, data.grain,
    data.year_from, data.year_to, shown.map((s) => s.key), alerts]);
  useEffect(() => {
    if (signature !== previous.current) {
      previous.current = signature;
      setOpen(severity === "danger");
    }
  }, [signature, severity]);
  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !head.current?.contains(event.target)) setOpen(false);
    };
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setOpen(false);
      toggle.current?.focus();
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [open]);
  const how = t("seasonalSum", { from: data.year_from, to: data.year_to });
  const buttonLabel = t(`chartInfo.button.${severity ?? "normal"}`);
  return <div className="seasonal-result">
    <div className="chart-head" ref={head}>
      {heading}
      <button ref={toggle} type="button" className={`info-button${severity ? ` is-${severity}` : ""}`}
        aria-expanded={open} aria-controls={infoId} aria-label={buttonLabel} title={buttonLabel}
        onClick={() => setOpen((v) => !v)}>
        <span className="info-symbol"><InfoIcon /></span>
      </button>
      {open ? <div id={infoId} className="chart-info caption" role="note" aria-label={t("chartInfo.title")}>
        <strong>{t("chartInfo.title")}</strong>
        <p>{how}</p>
        {severity ? <div className={`seasonal-alerts is-${severity}`} role={severity === "danger" ? "alert" : "status"}>
          <strong>{t(`seasonalRisk.${severity}`)}</strong>
          <ul>{alerts.map((p) => <li key={`${p.label}|${p.part}`}>
            <strong>{p.part === "ano" ? t("seasonalYear") : partLabel(p.part)} · {p.label}: </strong>
            {p.blocked.length || p.present || !p.missing.length ? t(
              p.blocked.length ? "seasonalBlocked" : p.present ? "seasonalCoverage" : "seasonalEmpty",
              { present: p.present, expected: p.expected },
            ) : null}
            {p.missing.length ? <span> {t("seasonalMissing", { periods: p.missing.map(formatPeriod).join(", ") })}</span> : null}
            {p.blocked.length ? <span> {t("seasonalBlockedParts", { periods: p.blocked.map(formatPeriod).join(", ") })}</span> : null}
            {p.input_partial.length ? <span> {t("seasonalInputPartial")}</span> : null}
          </li>)}</ul>
        </div> : null}
        <p>{t("seasonalScope")}</p>
        <details className="seasonal-notes"><summary>{t("seasonalValues")}</summary>
          <ul>{shown.flatMap((s) => s.points.map((p) => <li key={`${s.key}|${p.part}`}>
            {p.part === "ano" ? t("seasonalYear") : partLabel(p.part)} · {s.label}: {formatValue(p.value, p.status)}. {t("seasonalCoverage", { present: p.present, expected: p.expected })}
          </li>))}</ul>
        </details>
        {data.notes.length ? <details className="seasonal-notes"><summary>{t("seasonalNotes")}</summary>
          <ul>{data.notes.map((note, i) => <li key={i}>{note}</li>)}</ul>
        </details> : null}
      </div> : null}
    </div>
    <SeasonPlot bars={bars} labels={labels} how={how} unit={data.unit} showMethod={false} />
  </div>;
}
