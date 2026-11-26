"use client";

// Painel das contas (ADR-0039, seção 4). Mesma moldura do Painel das Estatísticas oficiais
// (barra lateral + área central), organizada pela pergunta: quanto, onde, como, quando e
// quem recebeu. Só a lente A. Os dados chegam prontos (client tipado de /contas/*).
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { FaIcon } from "@/components/FaIcon";
import { FA } from "@/lib/faIcons";
import { MOBILE_QUERY, useMediaQuery } from "@/lib/useMediaQuery";

export interface TrailItem {
  key: string | null;
  label: string;
}

export interface AreaOption {
  code: string;
  label: string;
}

/** Barra lateral: só território, período e área (opcional). */
export function ContasSidebar({ trail, territories, periods, period, areas, area, onTerritory, onPeriod, onArea, onClear, canClear }: {
  trail: TrailItem[];
  territories: { key: string; label: string }[];
  periods: { code: string; label: string }[];
  period: string;
  areas: AreaOption[];
  area: string | null;
  onTerritory: (key: string) => void;
  onPeriod: (period: string) => void;
  onArea: (area: string) => void;
  onClear: () => void;
  canClear: boolean;
}) {
  const t = useTranslations("contas");
  const mobile = useMediaQuery(MOBILE_QUERY);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const here = trail[trail.length - 1];
  return (
    <aside className="sidebar contas-sidebar">
      <div className="sb-current contas-current">
        <span className="contas-current-icon" aria-hidden="true"><FaIcon icon={FA.contas} size={18} /></span>
        <div>
          <p className="sb-crumb">{t("blockName")}</p>
          <p className="sb-kpi">{t("lensName")}</p>
        </div>
      </div>
      <section className="filters" aria-label={t("filters")}>
        {mobile ? (
          <button type="button" className="contas-filter-toggle" aria-expanded={filtersOpen} aria-controls="contas-filtros" onClick={() => setFiltersOpen((o) => !o)}>{t("filters")}</button>
        ) : <h2>{t("filters")}</h2>}
        <div id="contas-filtros" hidden={mobile && !filtersOpen}>
        <div className="filters-body">
          <label className="field">
            {t("territory")}
            <select value={here?.key ?? "brasil:1"} onChange={(e) => onTerritory(e.target.value)}>
              <option value="brasil:1">{t("brasil")}</option>
              {territories.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
            </select>
          </label>
          <label className="field">
            {t("period")}
            <select value={period} onChange={(e) => onPeriod(e.target.value)}>
              {periods.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
            </select>
          </label>
          <label className="field">
            {t("area")}
            <select value={area ?? ""} onChange={(e) => onArea(e.target.value)}>
              <option value="">{t("allAreas")}</option>
              {areas.map((a) => <option key={a.code} value={a.code}>{a.label}</option>)}
            </select>
          </label>
        </div>
        <div className="filters-foot"><button type="button" className="clear" disabled={!canClear} onClick={onClear}>{t("resetFilters")}</button></div>
        </div>
      </section>
    </aside>
  );
}

/** Moldura da área central: título, destaques e as seções na ordem da pergunta. */
export function ContasPanel({ crumb, title, status, highlights, map, how, when, who, foot }: {
  crumb: string;
  title: string;
  status: ReactNode;
  highlights: ReactNode;
  map: ReactNode;
  how: ReactNode;
  when: ReactNode;
  who: ReactNode;
  foot: ReactNode;
}) {
  const t = useTranslations("contas");
  return (
    <div className="contas-grid">
      <header className="contas-head">
        <div className="page-title">
          <p className="crumb">{crumb}</p>
          <h1>{title}</h1>
        </div>
        {status}
      </header>
      {highlights}
      <section className="contas-section card contas-where" aria-labelledby="onde">
        <h2 id="onde" className="contas-section-title"><FaIcon icon={FA.municipio} size={16} />{t("map.title")}</h2>
        {map}
      </section>
      <section className="contas-section card contas-how-card" aria-labelledby="como">
        <h2 id="como" className="contas-section-title"><FaIcon icon={FA.transferidos} size={16} />{t("how.title")}</h2>
        {how}
      </section>
      <section className="contas-section card contas-when" aria-labelledby="quando">
        <h2 id="quando" className="contas-section-title"><FaIcon icon={FA.contasNacionais} size={16} />{t("when.title")}</h2>
        {when}
      </section>
      <section className="contas-section card contas-who" aria-labelledby="quem">
        <h2 id="quem" className="contas-section-title"><FaIcon icon={FA.recebimento} size={16} />{t("who.title")}</h2>
        {who}
      </section>
      <footer className="contas-foot card">{foot}</footer>
    </div>
  );
}
