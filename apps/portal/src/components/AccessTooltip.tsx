"use client";

import { useTranslations } from "next-intl";

import { useValueLabels } from "@/components/useValueLabels";
import { formatPct, viewsText, type GeoItem } from "@/lib/metrics";

interface Props {
  item: GeoItem;
  /** Período por extenso ("18 de out. de 2026 – 16 de nov. de 2026"). */
  period: string;
  /** Posição dentro do mapa, em px (canto superior esquerdo do tooltip). */
  x?: number | string;
  y?: number | string;
  /** "card": cartão fixo abaixo do mapa (toque no celular), com botão de fechar. */
  variant?: "tooltip" | "card";
  onClose?: () => void;
}

// Tooltip de acessos (DS 2.12): o visual do DetailTooltip (faixa da marca, superfície e
// sombra), com os campos de acesso: visualizações, % do total e período. "Menos de 5" e
// "sem acessos" substituem o número quando a API suprime ou não há acesso.
export function AccessTooltip({ item, period, x = 0, y = 0, variant = "tooltip", onClose }: Props) {
  const t = useTranslations("metrics");
  const labels = useValueLabels();
  const share = item.status === "ok" && item.share_pct !== null ? formatPct(item.share_pct) : null;
  const body = (
    <>
      <div className="tt-stripe" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="tt-body">
        <div className="tt-head">
          <span className="tt-name">{item.name}</span>
          <span className="tt-period">{period}</span>
        </div>
        <div className="tt-total">
          <span className="tt-total-value">{viewsText(item, labels)}</span>
          {item.status === "ok" ? <span className="tt-unit">{t("map.views")}</span> : null}
        </div>
        {share ? <p className="access-tip-share">{t("tip.share", { pct: share })}</p> : null}
      </div>
    </>
  );
  if (variant === "card") {
    return (
      <section className="access-card" aria-live="polite">
        {body}
        {onClose ? (
          <button type="button" className="btn-outline access-card-close" onClick={onClose}>
            {t("card.close")}
          </button>
        ) : null}
      </section>
    );
  }
  return (
    <div className="access-tip" role="tooltip" style={{ left: x, top: y }}>
      {body}
    </div>
  );
}
