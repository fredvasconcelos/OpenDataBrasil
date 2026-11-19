"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { PeriodFilter } from "@/components/PeriodFilter";
import { grainPeriods } from "@/lib/state";
import { useAsync } from "@/lib/useAsync";
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
  periods?: string[];
  /** Filtro do Detalhar por (DS 2.4): a exportação segue o painel. */
  categories?: string[];
  /** Grão de tempo do painel (ADR-0013); null: o publicado. */
  grain?: string | null;
  correction?: string | null;
}

/** Teto por KPI: só os dois LSPA receberam 200 mil em 18/11/2026. */
export function exportRowLimit(kpiId: string): number {
  return kpiId === "safra_estimada" || kpiId === "safra_area_colhida" ? 200_000 : 10_000;
}

type GrainId = "mes" | "trimestre" | "semestre" | "ano";

/** Estimativa de linhas: territórios × períodos × combinações de categorias. */
export function estimateRows(kpi: Kpi, levels: readonly string[], grains: readonly string[], dims: readonly string[], crossable: boolean, scope: { counts: Record<string, number>; periods: Record<string, string[]> }): number {
  const periods = (g: string, level: string) => scope.periods[g]?.length ?? grainPeriods(kpi, g || null, level).periods.length;
  const cats = (d: string) => (kpi.dimensions.find((x) => x.classification_id === d)?.categories.length ?? 0) + 1;
  const combos = crossable ? dims.reduce((n, d) => n * cats(d), 1) : 1 + dims.reduce((n, d) => n + cats(d) - 1, 0);
  const grainList = grains.length ? grains : [""];
  return levels.reduce((sum, l) => sum + (scope.counts[l] ?? 0) * grainList.reduce((n, g) => n + periods(g, l), 0) * combos, 0);
}

// "Exportar dados" (B5, DS 2.7): abre a janela com níveis, grãos, dimensões e formato.
// "Selecionar tudo" marca todos. O arquivo sai em formato longo, com as colunas nivel,
// grao e tipo (publicado ou derivado); nunca com valores acumulados (ADR-0026).
export function DataExport({ kpi, level, within = null, dimensions, periods: panelPeriods = [], categories = [], grain = null, correction = null }: DataProps) {
  const { busy, error, run, t } = useExportRun();
  const tl = useTranslations("levels");
  const [open, setOpen] = useState(false);
  const grains = kpi.time_grains ?? [];
  const levels = kpi.levels;
  const [chosenLevels, setLevels] = useState<string[]>([level]);
  const [chosenGrains, setGrains] = useState<string[]>(grains.length ? [grain ?? grains[0]!.grain] : []);
  const [chosenDims, setDims] = useState<string[]>(dimensions);
  const [chosenWithin, setWithin] = useState<string | null>(within);
  const [periodSelection, setPeriodSelection] = useState<Record<string, string[]>>({});
  const states = useAsync(open ? () => api.geographies("uf") : null, [open]);
  const [optionsRetry, setOptionsRetry] = useState(0);
  const options = useAsync(open ? () => api.exportOptions(kpi.kpi_id, chosenWithin) : null, [open, kpi.kpi_id, chosenWithin], optionsRetry);
  const [format, setFormat] = useState<ExportFormat>("csv");
  const dialog = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement>(null);

  const reset = () => {
    setLevels([level]);
    setGrains(grains.length ? [grain ?? grains[0]!.grain] : []);
    setDims(dimensions);
    setWithin(within);
    const currentGrain = grain ?? grains[0]?.grain ?? "";
    const available = grainPeriods(kpi, grain, level).periods;
    const selected = available.filter((p) => panelPeriods.includes(p));
    setPeriodSelection(selected.length ? { [currentGrain]: selected } : {});
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
    setPeriodSelection({});
  };
  const crossable = !kpi.exclusive_dimensions || chosenDims.length < 2;
  const grainList = chosenGrains.length ? chosenGrains : [""];
  const availablePeriods = (g: string) => {
    const lists = chosenLevels.map((l) => grainPeriods(kpi, g || null, l).periods);
    return (lists[0] ?? []).filter((p) => lists.every((list) => list.includes(p)));
  };
  const effectivePeriods = Object.fromEntries(grainList.map((g) => [g,
    periodSelection[g] ? availablePeriods(g).filter((p) => periodSelection[g]!.includes(p)) : availablePeriods(g),
  ]));
  const rows = options.data ? estimateRows(kpi, chosenLevels, chosenGrains, chosenDims, crossable, { counts: options.data.territory_counts, periods: Object.fromEntries(grainList.filter((g) => periodSelection[g]).map((g) => [g, effectivePeriods[g]!])) }) : null;
  const maxRows = options.data?.max_rows ?? exportRowLimit(kpi.kpi_id);
  const tooMany = rows !== null && rows > maxRows;
  const emptyPeriods = grainList.some((g) => !effectivePeriods[g]?.length);
  const excessiveSelection = grainList.some((g) => periodSelection[g] && (effectivePeriods[g]?.length ?? 0) > 120);
  const noTerritories = options.data && chosenLevels.every((l) => !options.data!.territory_counts[l]);
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
              <label className="field">
                {t("state")}
                <select value={chosenWithin ?? ""} onChange={(e) => setWithin(e.target.value || null)}>
                  <option value="">{t("wholeCountry")}</option>
                  {within && !within.startsWith("uf:") ? <option value={within}>{t("panelScope")}</option> : null}
                  {(states.data ?? []).map((geo) => <option key={geo.geography_key} value={geo.geography_key}>{geo.name}</option>)}
                </select>
              </label>
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
              <fieldset>
                <legend>{t("periodSelection")}</legend>
                <p className="muted small">{t("periodCoverage")}</p>
                {grainList.map((g) => {
                  const available = availablePeriods(g);
                  const selected = effectivePeriods[g] ?? [];
                  const name = grains.find((item) => item.grain === g)?.label ?? t("published");
                  return <details key={g} className="export-periods">
                    <summary>{name} · {periodSelection[g] ? t("selectedPeriods", { count: selected.length }) : t("allPeriods")}</summary>
                    <label className="check small">
                      <input type="checkbox" checked={!periodSelection[g]} onChange={(e) => setPeriodSelection((current) => {
                        const next = { ...current };
                        if (e.target.checked) delete next[g];
                        else next[g] = available.slice(-1);
                        return next;
                      })} />
                      {t("allPeriods")}
                    </label>
                    <PeriodFilter leaves={available} complete={grainPeriods(kpi, g || null).complete} selected={selected} onChange={(next) => setPeriodSelection((current) => ({ ...current, [g]: next }))} />
                  </details>;
                })}
              </fieldset>
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
              {rows === null ? t("estimating") : t(tooMany ? "estimateTooMany" : "estimate", { rows: rows.toLocaleString("pt-BR"), max: maxRows.toLocaleString("pt-BR") })}
            </p>
            {options.error ? <p className="error" role="alert">{t("optionsError")} <button type="button" onClick={() => setOptionsRetry((n) => n + 1)}>{t("retry")}</button></p> : null}
            {emptyPeriods ? <p className="error" role="alert">{t("choosePeriods")}</p> : null}
            {excessiveSelection ? <p className="error" role="alert">{t("periodLimit")}</p> : null}
            {noTerritories ? <p className="error" role="alert">{t("noTerritories")}</p> : null}
            {tooMany ? <p className="muted small">{t("fullExtract")} {process.env.NEXT_PUBLIC_CONTACT_URL ? <a href={process.env.NEXT_PUBLIC_CONTACT_URL}>{t("contact")}</a> : null}</p> : null}
            <p className="muted small">{t("neverAccumulated")}</p>
            <div className="export-dialog-actions">
              <button type="button" onClick={close}>
                {t("cancel")}
              </button>
              <button
                type="button"
                className="primary"
                disabled={busy || !options.data || emptyPeriods || excessiveSelection || Boolean(noTerritories)}
                onClick={() =>
                  run(async () => {
                    const { blob, filename } = await api.exportFile({
                      kpi_id: kpi.kpi_id,
                      level: chosenLevels[0] ?? level,
                      levels: chosenLevels,
                      grains: chosenGrains as GrainId[],
                      within: chosenWithin,
                      periods: [],
                      periods_by_grain: Object.fromEntries(grainList.filter((g) => periodSelection[g]).map((g) => [g || grains[0]?.grain || "ano", effectivePeriods[g]!])),
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
