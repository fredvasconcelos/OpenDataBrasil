"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { pngBlob, saveBlob, svgBlob } from "@/lib/download";
import type { ExportFormat, Kpi } from "@/lib/types";

// Design System ODBr: cada grupo de botões fica junto do que exporta.
//   MapImageExport → no cabeçalho do mapa (SVG, PNG da imagem do mapa).
//   DataExport     → no cabeçalho de "Gráfico e tabela": abre a janela de exportação (B5).
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
  kpi: Kpi;
  /** Nível, grão e dimensões do painel: o ponto de partida da janela. */
  level: string;
  /** Recorte do mapa: exporta só os territórios dentro dele. */
  within?: string | null;
  dimensions: string[];
  /** Filtro do Detalhar por (DS 2.4): a exportação segue o painel. */
  categories?: string[];
  /** Grão de tempo do painel (ADR-0013); null: o publicado. */
  grain?: string | null;
  correction?: string | null;
}

// Territórios por nível, para a estimativa de linhas da janela (teto, sem o recorte).
const LEVEL_SIZE: Record<string, number> = {
  brasil: 1,
  regiao: 5,
  uf: 27,
  regiao_metropolitana: 80,
  municipio: 5570,
  areas_pof: 12,
};
/** Teto por KPI: só os dois LSPA receberam 200 mil em 18/11/2026. */
export function exportRowLimit(kpiId: string): number {
  return kpiId === "safra_estimada" || kpiId === "safra_area_colhida" ? 200_000 : 100_000;
}

type GrainId = "mes" | "trimestre" | "semestre" | "ano";

/** Estimativa de linhas: territórios × períodos × combinações de categorias. */
export function estimateRows(kpi: Kpi, levels: readonly string[], grains: readonly string[], dims: readonly string[], crossable: boolean): number {
  const periods = (g: string) => kpi.time_grains?.find((x) => x.grain === g)?.periods.length ?? kpi.periods.length;
  const cats = (d: string) => (kpi.dimensions.find((x) => x.classification_id === d)?.categories.length ?? 0) + 1;
  const combos = crossable ? dims.reduce((n, d) => n * cats(d), 1) : 1 + dims.reduce((n, d) => n + cats(d) - 1, 0);
  const grainList = grains.length ? grains : [""];
  return levels.reduce((sum, l) => sum + (LEVEL_SIZE[l] ?? 100) * grainList.reduce((n, g) => n + periods(g), 0) * combos, 0);
}

// "Exportar dados" (B5, DS 2.7): abre a janela com níveis, grãos, dimensões e formato.
// "Selecionar tudo" marca todos. O arquivo sai em formato longo, com as colunas nivel,
// grao e tipo (publicado ou derivado); nunca com valores acumulados (ADR-0026).
export function DataExport({ kpi, level, within = null, dimensions, categories = [], grain = null, correction = null }: DataProps) {
  const { busy, error, run, t } = useExportRun();
  const tl = useTranslations("levels");
  const [open, setOpen] = useState(false);
  const grains = kpi.time_grains ?? [];
  const levels = kpi.levels;
  const [chosenLevels, setLevels] = useState<string[]>([level]);
  const [chosenGrains, setGrains] = useState<string[]>(grains.length ? [grain ?? grains[0]!.grain] : []);
  const [chosenDims, setDims] = useState<string[]>(dimensions);
  const [format, setFormat] = useState<ExportFormat>("csv");
  const dialog = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement>(null);

  const reset = () => {
    setLevels([level]);
    setGrains(grains.length ? [grain ?? grains[0]!.grain] : []);
    setDims(dimensions);
  };
  const close = () => {
    setOpen(false);
    opener.current?.focus();
  };
  useEffect(() => {
    if (!open) return;
    dialog.current?.querySelector<HTMLElement>("input, button")?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const all = chosenLevels.length === levels.length && chosenGrains.length === grains.length && chosenDims.length === kpi.dimensions.length;
  const selectAll = () => {
    setLevels(levels);
    setGrains(grains.map((g) => g.grain));
    setDims(kpi.dimensions.map((d) => d.classification_id));
  };
  const crossable = !kpi.exclusive_dimensions || chosenDims.length < 2;
  const rows = estimateRows(kpi, chosenLevels, chosenGrains, chosenDims, crossable);
  const maxRows = exportRowLimit(kpi.kpi_id);
  const tooMany = rows > maxRows;
  const toggle = (list: string[], set: (v: string[]) => void, order: string[], id: string, on: boolean) =>
    set(order.filter((x) => (x === id ? on : list.includes(x))));

  return (
    <div className="export-wrap">
      <div className="export" aria-busy={busy}>
        <button
          ref={opener}
          type="button"
          className="primary"
          aria-haspopup="dialog"
          onClick={() => {
            reset();
            setOpen(true);
          }}
        >
          {t("openDialog")}
        </button>
        {busy ? <span className="muted">{t("running")}</span> : null}
      </div>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {open ? (
        <>
          <button type="button" className="dialog-backdrop" tabIndex={-1} aria-label={t("cancel")} onClick={close} />
          <div ref={dialog} className="export-dialog" role="dialog" aria-modal="true" aria-labelledby="export-title">
            <div className="export-dialog-head">
              <h2 id="export-title">{t("dialogTitle")}</h2>
              <button type="button" className="text-btn" onClick={all ? reset : selectAll}>
                {all ? t("selectCurrent") : t("selectAll")}
              </button>
            </div>
            <p className="muted small">{t("dialogLead")}</p>
            <div className="export-dialog-body">
              <fieldset>
                <legend>{t("levels")}</legend>
                {levels.map((l) => (
                  <label key={l} className="check small">
                    <input
                      type="checkbox"
                      checked={chosenLevels.includes(l)}
                      disabled={chosenLevels.length === 1 && chosenLevels.includes(l)}
                      onChange={(e) => toggle(chosenLevels, setLevels, levels, l, e.target.checked)}
                    />
                    {tl(l)}
                  </label>
                ))}
              </fieldset>
              {grains.length ? (
                <fieldset>
                  <legend>{t("grains")}</legend>
                  {grains.map((g, i) => (
                    <label key={g.grain} className="check small">
                      <input
                        type="checkbox"
                        checked={chosenGrains.includes(g.grain)}
                        disabled={chosenGrains.length === 1 && chosenGrains.includes(g.grain)}
                        onChange={(e) => toggle(chosenGrains, setGrains, grains.map((x) => x.grain), g.grain, e.target.checked)}
                      />
                      {g.label}
                      <span className="check-note">{i === 0 ? t("published") : t("derived")}</span>
                    </label>
                  ))}
                </fieldset>
              ) : null}
              {kpi.dimensions.length ? (
                <fieldset>
                  <legend>{t("dimensions")}</legend>
                  {kpi.dimensions.map((d) => (
                    <label key={d.classification_id} className="check small">
                      <input
                        type="checkbox"
                        checked={chosenDims.includes(d.classification_id)}
                        onChange={(e) =>
                          toggle(chosenDims, setDims, kpi.dimensions.map((x) => x.classification_id), d.classification_id, e.target.checked)
                        }
                      />
                      {d.label}
                    </label>
                  ))}
                  {!crossable ? <p className="grain-note">{t("marginal")}</p> : null}
                </fieldset>
              ) : null}
              <fieldset>
                <legend>{t("format")}</legend>
                {FORMATS.map((f) => (
                  <label key={f.id} className="check small">
                    <input type="radio" name="formato" checked={format === f.id} onChange={() => setFormat(f.id)} />
                    {f.label}
                  </label>
                ))}
              </fieldset>
            </div>
            <p className={tooMany ? "error" : "muted small"} role="status">
              {t(tooMany ? "estimateTooMany" : "estimate", { rows: rows.toLocaleString("pt-BR"), max: maxRows.toLocaleString("pt-BR") })}
            </p>
            <p className="muted small">{t("neverAccumulated")}</p>
            <div className="export-dialog-actions">
              <button type="button" onClick={close}>
                {t("cancel")}
              </button>
              <button
                type="button"
                className="primary"
                disabled={busy || tooMany}
                onClick={() =>
                  run(async () => {
                    const { blob, filename } = await api.exportFile({
                      kpi_id: kpi.kpi_id,
                      level: chosenLevels[0] ?? level,
                      levels: chosenLevels,
                      grains: chosenGrains as GrainId[],
                      within,
                      periods: [],
                      dimensions: chosenDims,
                      categories: categories.filter((c) => chosenDims.includes(c.split(":")[0] ?? "")),
                      correction,
                      format,
                    });
                    saveBlob(blob, filename);
                    close();
                  })
                }
              >
                {t("download")}
              </button>
            </div>
          </div>
        </>
      ) : null}
    </div>
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
