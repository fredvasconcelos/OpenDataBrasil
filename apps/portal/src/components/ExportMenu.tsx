"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { api } from "@/lib/api";
import { pngBlob, saveBlob, svgBlob } from "@/lib/download";
import type { ExportFormat } from "@/lib/types";

interface Props {
  kpiId: string;
  level: string;
  period: string | null;
  dimensions: string[];
  svg: () => SVGSVGElement | null;
  caption: string;
  filename: string;
}

const FORMATS: { id: ExportFormat; label: string }[] = [
  { id: "csv", label: "CSV" },
  { id: "xlsx", label: "XLSX" },
  { id: "parquet", label: "Parquet" },
  { id: "json", label: "JSON" },
];

export function ExportMenu({ kpiId, level, period, dimensions, svg, caption, filename }: Props) {
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

  return (
    <div className="small" role="group" aria-label={t("title")}>
      <strong>{t("data")}:</strong>{" "}
      {FORMATS.map((f) => (
        <button
          key={f.id}
          type="button"
          disabled={busy}
          onClick={() =>
            run(async () => {
              const { blob, filename: name } = await api.exportFile({
                kpi_id: kpiId,
                level,
                periods: period ? [period] : [],
                dimensions,
                format: f.id,
              });
              saveBlob(blob, name);
            })
          }
        >
          {f.label}
        </button>
      ))}{" "}
      <strong>{t("image")}:</strong>{" "}
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
      {busy ? <span className="muted"> {t("running")}</span> : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
