"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { ThemeIcon } from "@/components/ThemeIcon";
import { type CatalogKpi, dimensionsText, periodRange } from "@/lib/catalog";
import { themeStyle, themeVisual } from "@/lib/themes";

interface Props {
  item: CatalogKpi;
  releaseId: string | null;
  onClose: () => void;
}

// Prévia do indicador (pop-up do Início, Design System ODBr v2.3): faixa na cor do tema
// com caminho e situação, nome, descrição, metadados, limitações e "Abrir no painel".
// Diálogo modal: foco vai para "Fechar", Esc ou clique no véu fecham, o foco volta ao botão de origem.
export function KpiPreview({ item, releaseId, onClose }: Props) {
  const t = useTranslations();
  const close = useRef<HTMLButtonElement>(null);
  const { kpi } = item;
  const visual = themeVisual(item.theme);
  const dims = dimensionsText(kpi);
  const level = (l: string) => (t.has(`levels.${l}`) ? t(`levels.${l}`) : l);

  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      before?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="modal-layer">
      <div className="modal-veil" onClick={onClose} aria-hidden="true" />
      <div className="kpi-preview" role="dialog" aria-modal="true" aria-labelledby="kpi-preview-title" style={themeStyle(visual.family)}>
        <div className="kpi-preview-band">
          <ThemeIcon icon={visual.icon} size={20} />
          <span className="kpi-preview-path">
            {item.themeLabel}
            {item.subthemeLabel ? ` › ${item.subthemeLabel}` : ""}
          </span>
          <span className="status ok">{t("catalog.published")}</span>
          <button ref={close} type="button" className="modal-close" aria-label={t("catalog.close")} onClick={onClose}>
            ×
          </button>
        </div>
        <div className="kpi-preview-body">
          <h2 id="kpi-preview-title">{kpi.label}</h2>
          {kpi.description ? <p className="kpi-preview-desc">{kpi.description}</p> : null}
          <dl className="meta">
            <dt>{t("catalog.source")}</dt>
            <dd>
              {t("catalog.table", { id: kpi.source.source_table_id })}
              {kpi.source.reference_url ? (
                <>
                  {" · "}
                  <a href={kpi.source.reference_url} target="_blank" rel="noopener noreferrer">
                    {t("catalog.officialSource")}
                  </a>
                </>
              ) : null}
            </dd>
            <dt>{t("catalog.mainDimension")}</dt>
            <dd>{dims.main ?? t("catalog.totalOnly")}</dd>
            <dt>{t("catalog.otherDimensions")}</dt>
            <dd>{dims.others ?? "—"}</dd>
            <dt>{t("catalog.unit")}</dt>
            <dd>{kpi.unit || "—"}</dd>
            <dt>{t("catalog.periods")}</dt>
            <dd>{periodRange(kpi.periods)}</dd>
            <dt>{t("catalog.mapLevels")}</dt>
            <dd className="pills">
              {kpi.map_levels.length ? kpi.map_levels.map((l) => <span key={l}>{level(l)}</span>) : "—"}
            </dd>
            <dt>{t("catalog.license")}</dt>
            <dd>{kpi.source.license_id ?? "—"}</dd>
            {releaseId ? (
              <>
                <dt>{t("catalog.version")}</dt>
                <dd className="mono">{releaseId}</dd>
              </>
            ) : null}
          </dl>
          {kpi.caveats.length ? (
            <div className="kpi-preview-caveats">
              <h3>{t("catalog.caveats")}</h3>
              <ul>
                {kpi.caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="kpi-preview-actions">
            <Link className="btn-primary" href={`/dashboard?kpi=${encodeURIComponent(kpi.kpi_id)}`}>
              {t("home.open")}
            </Link>
            <span className="muted small">{t("catalog.escCloses")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
