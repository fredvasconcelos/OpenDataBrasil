"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { api } from "@/lib/api";
import { pngBlob, saveBlob, svgBlob } from "@/lib/download";
import type { ExportFormat } from "@/lib/types";

// Design System ODBr: cada grupo de botões fica junto do que exporta.
//   MapImageExport → no cabeçalho do mapa (SVG, PNG da imagem do mapa).
//   DataExport     → no cabeçalho de "Gráfico e tabela" (CSV, XLSX, Parquet, JSON).
// Durante a exportação: botões desabilitados, aria-busy e "Gerando arquivo…".

const FORMATS: { id: ExportFormat; label: string }[] = [
  { id: "csv", label: "CSV" },
  { id: "xlsx", label: "XLSX" },
  { id: "parquet", label: "Parquet" },
  { id: "json", label: "JSON" },
];

function useExportRun() {
  const t = useTranslations("export");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (e) {
      setError(t("failed", { message: e instanceof Error ? e.message : String(e) }));
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run, t };
}

function Group({ label, busy, error, running, children }: { label: string; busy: boolean; error: string | null; running: string; children: React.ReactNode }) {
  return (
    <div className="export-wrap">
      <div className="export" role="group" aria-label={label} aria-busy={busy}>
        <span className="export-label">{label}</span>
        {children}
        {busy ? <span className="muted">{running}</span> : null}
      </div>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

interface DataProps {
  kpiId: string;
  level: string;
  /** Recorte do mapa: exporta só os territórios dentro dele. */
  within?: string | null;
  period: string | null;
  dimensions: string[];
  /** Grão de tempo somado (ADR-0013); null: os valores publicados. */
  grain?: "mes" | "trimestre" | "semestre" | "ano" | null;
  correction?: string | null;
}

export function DataExport({ kpiId, level, within = null, period, dimensions, grain = null, correction = null }: DataProps) {
  const { busy, error, run, t } = useExportRun();
  return (
    <Group label={t("download")} busy={busy} error={error} running={t("running")}>
      {FORMATS.map((f) => (
        <button
          key={f.id}
          type="button"
          disabled={busy}
          onClick={() =>
            run(async () => {
              const { blob, filename } = await api.exportFile({
                kpi_id: kpiId,
                level,
                within,
                periods: period ? [period] : [],
                dimensions,
                grain,
                correction,
                format: f.id,
              });
              saveBlob(blob, filename);
            })
          }
        >
          {f.label}
        </button>
      ))}
    </Group>
  );
}

interface MapProps {
  svg: () => SVGSVGElement | null;
  caption: string;
  filename: string;
}

export function MapImageExport({ svg, caption, filename }: MapProps) {
  const { busy, error, run, t } = useExportRun();
  return (
    <Group label={t("image")} busy={busy} error={error} running={t("running")}>
      <button
        type="button"
        disabled={busy}
        onClick={() =>
          run(async () => {
            const el = svg();
            if (el) saveBlob(svgBlob(el, caption), `${filename}.svg`);
          })
        }
      >
        SVG
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={() =>
          run(async () => {
            const el = svg();
            if (el) saveBlob(await pngBlob(el, caption), `${filename}.png`);
          })
        }
      >
        PNG
      </button>
    </Group>
  );
}
