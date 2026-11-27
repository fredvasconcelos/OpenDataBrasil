"use client";

// Painel das contas (ADR-0039, seção 4). Mesma moldura do Painel das Estatísticas oficiais
// (barra lateral + área central), organizada pela pergunta: quanto, onde, como, quando e
// quem recebeu. Só a lente A. Os dados chegam prontos (client tipado de /contas/*).
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { FaIcon } from "@/components/FaIcon";
import { ContasIndicatorTree } from "@/components/contas/ContasIndicatorTree";
import type { ContasMeta } from "@/lib/contas/types";
import { ContasInfo } from "@/components/contas/ContasInfo";
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
export function ContasSidebar({ trail = [], territories = [], periods = [], period = "", areas = [], area = null, onTerritory, onPeriod, onArea, onClear, canClear, meta, lensLabel, controls }: {
  meta?: ContasMeta;
  lensLabel?: string;
  controls?: ReactNode;
  trail?: TrailItem[];
  territories?: { key: string; label: string }[];
  periods?: { code: string; label: string }[];
  period?: string;
  areas?: AreaOption[];
  area?: string | null;
  onTerritory?: (key: string) => void;
  onPeriod?: (period: string) => void;
  onArea?: (area: string) => void;
  onClear: () => void;
  canClear: boolean;
}) {
  const t = useTranslations("contas");
  const mobile = useMediaQuery(MOBILE_QUERY);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const here = trail[trail.length - 1];
  return (
    // Mesma marcação da barra das Estatísticas (Sidebar.tsx): indicador atual, filtros e,
    // no pé, a limpeza. No celular, os filtros recolhem atrás de um botão.
    <aside className="sidebar contas-sidebar">
      <div className="sb-current">
        <p className="sb-crumb">{t("blockName")}</p>
        <p className="sb-kpi">{lensLabel ?? t("lensName")}</p>
      </div>
      <section className="filters" aria-label={t("filters")}>
        {mobile ? (
          <button type="button" className="contas-filter-toggle" aria-label={t("filters")} aria-expanded={filtersOpen} aria-controls="contas-filtros" onClick={() => setFiltersOpen((o) => !o)}>{t("filters")}</button>
        ) : <h2>{t("filters")}</h2>}
        <div id="contas-filtros" className="contas-filters" hidden={mobile && !filtersOpen}>
        <div className="filters-body">
          {controls ?? <><label className="field">
            {t("territory")}
            <select value={here?.key ?? "brasil:1"} onChange={(e) => onTerritory?.(e.target.value)}>
              <option value="brasil:1">{t("brasil")}</option>
              {territories.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
            </select>
          </label>
          <label className="field">
            {t("period")}
            <select value={period} onChange={(e) => onPeriod?.(e.target.value)}>
              {periods.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
            </select>
          </label>
          <label className="field">
            {t("area")}
            <select value={area ?? ""} onChange={(e) => onArea?.(e.target.value)}>
              <option value="">{t("allAreas")}</option>
              {areas.map((a) => <option key={a.code} value={a.code}>{a.label}</option>)}
            </select>
          </label>
          </>}
        </div>
        <div className="filters-foot"><button type="button" className="clear" disabled={!canClear} onClick={onClear}>{t("resetFilters")}</button></div>
        </div>
      </section>
      {meta ? <ContasIndicatorTree meta={meta} /> : null}
    </aside>
  );
}

/** Moldura da área central: título, destaques e as seções na ordem da pergunta.
 *  Cada seção tem um botão i com as notas de origem e de uso (mesmo padrão das Estatísticas). */
export function ContasPanel({ crumb, title, status, highlights, map, how, when, who, foot, info, scope }: {
  crumb: string;
  title: string;
  status: ReactNode;
  highlights: ReactNode;
  map: ReactNode;
  how: ReactNode;
  when: ReactNode;
  who: ReactNode;
  foot: ReactNode;
  info: { map: ReactNode; how: ReactNode; when: ReactNode };
  /** Recorte de área, repetido no título das seções filtradas (ex.: "Saúde"). */
  scope?: string | null;
}) {
  const t = useTranslations("contas");
  // A lista de áreas mostra sempre todas as áreas: só mapa, evolução e recebedores levam o recorte no título.
  const head = (id: string, icon: Parameters<typeof FaIcon>[0]["icon"], label: string, body: ReactNode, about: string, scoped = true) => (
    <ContasInfo label={about} title={<h2 id={id} className="contas-section-title"><FaIcon icon={icon} size={16} />{label}{scoped && scope ? <span className="contas-section-scope"> · {scope}</span> : null}</h2>}>
      {body}
    </ContasInfo>
  );
  return (
    <div className="contas-grid">
      <ContasPanelHead crumb={crumb} title={title} status={status} />
      {highlights}
      <section className="contas-section card contas-where" aria-labelledby="onde">
        {head("onde", FA.municipio, t("map.title"), info.map, t("info.map"))}
        {map}
      </section>
      <section className="contas-section card contas-how-card" aria-labelledby="como">
        {head("como", FA.transferidos, t("how.title"), info.how, t("info.how"), false)}
        {how}
      </section>
      <section className="contas-section card contas-when" aria-labelledby="quando">
        {head("quando", FA.contasNacionais, t("when.title"), info.when, t("info.when"))}
        {when}
      </section>
      <section className="contas-section card contas-who" aria-labelledby="quem">
        <h2 id="quem" className="contas-section-title"><FaIcon icon={FA.recebimento} size={16} />{t("who.title")}{scope ? <span className="contas-section-scope"> · {scope}</span> : null}</h2>
        {who}
      </section>
      <div className="area-meta contas-foot">{foot}</div>
    </div>
  );
}


/** Cabeçalho comum: título e situação do período nas três lentes. */
export function ContasPanelHead({ crumb, title, status, info, infoLabel }: {
  crumb: string; title: string; status: ReactNode; info?: ReactNode; infoLabel?: string;
}) {
  return <header className="contas-head"><div className="page-title"><p className="crumb">{crumb}</p>{info && infoLabel ? <ContasInfo label={infoLabel} title={<h1>{title}</h1>}>{info}</ContasInfo> : <h1>{title}</h1>}</div>{status}</header>;
}
