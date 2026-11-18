"use client";

import { useLayoutEffect, useRef } from "react";

import { useTranslations } from "next-intl";

import { useValueLabels } from "@/components/useValueLabels";
import { formatPct, viewsText, type GeoItem } from "@/lib/metrics";

interface Props {
  item: GeoItem;
  /** Período por extenso ("18 de out. de 2026 – 16 de nov. de 2026"). */
  period?: string;
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
export function AccessTooltip({ item, x = 0, y = 0, variant = "tooltip", onClose }: Props) {
  const tip = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const node = tip.current;
    const parent = node?.parentElement;
    if (!node || !parent) return;
    const place = () => {
      const width = parent.clientWidth;
      const height = parent.clientHeight;
      const px = typeof x === "string" ? parseFloat(x) / 100 * width : x;
      const py = typeof y === "string" ? parseFloat(y) / 100 * height : y;
      node.style.left = `${Math.max(8, Math.min(width - node.offsetWidth - 8, px + 16))}px`;
      node.style.top = `${Math.max(8, Math.min(height - node.offsetHeight - 8, py - node.offsetHeight / 2))}px`;
    };
    place();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(place);
    observer.observe(parent);
    return () => observer.disconnect();
  }, [x, y, item, variant]);
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
        </div>
        <div className="tt-total">
          <span className="tt-total-value">{viewsText(item, labels)}</span>
          {item.status === "ok" ? <span className="tt-unit">{t("map.views")}</span> : null}
        </div>
        {share ? <p className="access-tip-share">{t(item.geography_key.startsWith("uf:") ? "tip.shareBrazil" : "tip.shareGlobal", { pct: share })}</p> : null}
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
    <div ref={tip} className="access-tip" role="tooltip" style={{ left: x, top: y }}>
      {body}
    </div>
  );
}
