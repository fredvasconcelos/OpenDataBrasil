"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { SearchGlyph } from "@/components/HomeCatalog";
import { ThemeIcon } from "@/components/ThemeIcon";
import { type CatalogKpi, type CatalogPlanned, dimensionsText, flatten, flattenPlanned, matchKpi, matchPlanned, periodRange } from "@/lib/catalog";
import { THEME_ICONS, themeStyle, themeVisual } from "@/lib/themes";
import type { Navigation } from "@/lib/types";

interface Props {
  nav: Navigation;
  releaseId: string | null;
  /** Data de ativação já formatada (pt-BR), ou null. */
  activated: string | null;
  /** Situação da licença dos dados, como vem de /datasets (ex.: "requires_review"). */
  licenseReview: string | null;
}

// Sobre os dados (Design System ODBr v2.3): release ativo e números; busca (nome, tema,
// subtema, tabela) e etiquetas de tema; um acordeão por tema com uma linha por indicador
// (tabela, dimensão principal, outras classificações). A linha abre com descrição,
// limitações, metadados e "Abrir no painel". Filtro de situação (Todos, Publicados, Em
// preparação): os indicadores em preparação (panorama) têm linha própria, sem painel.

type Status = "all" | "published" | "planned";
const SIDRA_TABLE_URL = "https://sidra.ibge.gov.br/tabela/";
export function AboutCatalog({ nav, releaseId, activated, licenseReview }: Props) {
  const t = useTranslations();
  const [q, setQ] = useState("");
  const [theme, setTheme] = useState("all");
  const [openTheme, setOpenTheme] = useState<string | null>(nav.themes[0]?.theme_id ?? null);
  const [openRow, setOpenRow] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("all");
  const items = useMemo(() => flatten(nav), [nav]);
  const pending = useMemo(() => flattenPlanned(nav), [nav]);
  const query = q.trim();
  const inTheme = (id: string) => theme === "all" || id === theme;
  const found =
    status === "planned" ? [] : items.filter((it) => inTheme(it.theme.theme_id) && (!query || matchKpi(it, query)));
  const foundPending =
    status === "published" ? [] : pending.filter((it) => inTheme(it.theme.theme_id) && (!query || matchPlanned(it, query)));
  const tables = new Set(items.map((it) => it.kpi.source.source_table_id));
  const level = (l: string) => (t.has(`levels.${l}`) ? t(`levels.${l}`) : l);

  return (
    <>
      <section className="about-stats" aria-label={t("about.release")}>
        <div className="about-release">
          <h2 className="eyebrow">{t("about.release")}</h2>
          <code>{releaseId ?? "—"}</code>
          {activated ? <span className="muted small">{t("about.activated", { date: activated })}</span> : null}
          {licenseReview ? <span className="warning-pill">{t("about.licenseReview", { status: licenseReview })}</span> : null}
        </div>
        <Stat value={items.length} label={t("catalog.statKpis")} tone="ok" />
        <Stat value={pending.length} label={t("catalog.statPlanned")} tone="muted" />
        <Stat value={nav.themes.length} label={t("catalog.statThemes")} />
        <Stat value={tables.size} label={t("catalog.statTables")} tone="link" />
      </section>

      <section className="about-filters">
        <div role="search" className="about-search">
          <label htmlFor="sobre-busca">{t("about.searchLabel")}</label>
          <SearchGlyph />
          <input id="sobre-busca" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("about.searchPlaceholder")} />
        </div>
        <div className="status-filter" role="group" aria-label={t("catalog.statusFilter")}>
          {(
            [
              ["all", t("catalog.statusAll")],
              ["published", t("catalog.statusPublished")],
              ["planned", t("catalog.statusPlanned")],
            ] as const
          ).map(([value, label]) => (
            <button key={value} type="button" aria-pressed={status === value} onClick={() => setStatus(value)}>
              {label}
            </button>
          ))}
        </div>
        <div className="theme-chips-row" role="group" aria-label={t("catalog.filterByTheme")}>
          <button type="button" className="theme-chip" aria-pressed={theme === "all"} onClick={() => setTheme("all")}>
            <span className="theme-chip-icon" aria-hidden="true">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d={THEME_ICONS.generico} />
              </svg>
            </span>
            {t("catalog.all")}
          </button>
          {nav.themes.map((th) => {
            const v = themeVisual(th);
            return (
              <button key={th.theme_id} type="button" className="theme-chip" aria-pressed={theme === th.theme_id} style={themeStyle(v.family)} onClick={() => setTheme(th.theme_id)}>
                <span className="theme-chip-icon" aria-hidden="true">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d={THEME_ICONS[v.icon]} />
                  </svg>
                </span>
                {th.label}
              </button>
            );
          })}
        </div>
      </section>

      {nav.themes.map((th) => {
        const rows = found.filter((it) => it.theme.theme_id === th.theme_id);
        const planned = foundPending.filter((it) => it.theme.theme_id === th.theme_id);
        if (!rows.length && !planned.length) return null;
        const v = themeVisual(th);
        const expanded = theme !== "all" || Boolean(query) || openTheme === th.theme_id;
        return (
          <section key={th.theme_id} className="about-theme" style={themeStyle(v.family)} aria-labelledby={`sobre-${th.theme_id}`}>
            <button
              type="button"
              className="about-theme-head"
              aria-expanded={expanded}
              onClick={() => setOpenTheme(openTheme === th.theme_id ? null : th.theme_id)}
            >
              <ThemeIcon icon={v.icon} />
              <span className="about-theme-title">
                <span id={`sobre-${th.theme_id}`}>{th.label}</span>
                <span>
                  {!planned.length
                    ? t("catalog.kpiCount", { count: rows.length })
                    : rows.length
                      ? `${t("catalog.kpiCount", { count: rows.length })} · ${t("catalog.plannedCount", { count: planned.length })}`
                      : t("catalog.plannedCount", { count: planned.length })}
                </span>
              </span>
              <Chevron open={expanded} />
            </button>
            {expanded ? (
              <div className="about-table">
                <div className="about-row about-row-head" aria-hidden="true">
                  <span>{t("about.colKpi")}</span>
                  <span>{t("about.colTable")}</span>
                  <span>{t("about.colStatus")}</span>
                  <span>{t("catalog.mainDimension")}</span>
                  <span>{t("catalog.otherDimensions")}</span>
                  <span />
                </div>
                {rows.map((it) => (
                  <Row
                    key={it.kpi.kpi_id}
                    item={it}
                    open={openRow === it.kpi.kpi_id}
                    onToggle={() => setOpenRow(openRow === it.kpi.kpi_id ? null : it.kpi.kpi_id)}
                    releaseId={releaseId}
                    level={level}
                  />
                ))}
                {planned.map((it) => (
                  <PlannedRow
                    key={it.planned.kpi_id}
                    item={it}
                    open={openRow === it.planned.kpi_id}
                    onToggle={() => setOpenRow(openRow === it.planned.kpi_id ? null : it.planned.kpi_id)}
                  />
                ))}
              </div>
            ) : null}
          </section>
        );
      })}
      {found.length === 0 && foundPending.length === 0 ? <p className="empty">{t("catalog.empty")}</p> : null}
    </>
  );
}

function Row({
  item,
  open,
  onToggle,
  releaseId,
  level,
}: {
  item: CatalogKpi;
  open: boolean;
  onToggle: () => void;
  releaseId: string | null;
  level: (l: string) => string;
}) {
  const t = useTranslations();
  const { kpi } = item;
  const dims = dimensionsText(kpi);
  const detail = `detalhe-${kpi.kpi_id}`;
  return (
    <div className={open ? "about-item open" : "about-item"}>
      <button type="button" className="about-row" aria-expanded={open} aria-controls={detail} onClick={onToggle}>
        <span className="about-name">
          <strong>{kpi.label}</strong>
          <span>{item.subthemeLabel || item.themeLabel}</span>
        </span>
        <span className="about-table-id">
          {kpi.source.source_table_id}
        </span>
        <span>
          <span className="status ok">{t("catalog.published")}</span>
        </span>
        <span>{dims.main ?? t("catalog.totalOnly")}</span>
        <span>{dims.others ?? "—"}</span>
        <span aria-hidden="true">
          <Chevron open={open} small />
        </span>
      </button>
      {open ? (
        <div id={detail} className="about-detail">
          <div>
            {kpi.description ? <p>{kpi.description}</p> : null}
            {kpi.caveats.length ? (
              <div>
                <h3>{t("catalog.caveats")}</h3>
                <ul>
                  {kpi.caveats.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="about-actions">
              <Link className="btn-primary small" href={`/dashboard?kpi=${encodeURIComponent(kpi.kpi_id)}`}>
                {t("home.open")}
              </Link>
              {kpi.source.reference_url ? (
                <a className="btn-outline" href={kpi.source.reference_url} target="_blank" rel="noopener noreferrer">
                  {t("about.tableAtSource", { id: kpi.source.source_table_id })}
                </a>
              ) : null}
            </div>
          </div>
          <dl className="meta">
            <dt>{t("catalog.unit")}</dt>
            <dd>{kpi.unit || "—"}</dd>
            <dt>{t("catalog.periods")}</dt>
            <dd>{periodRange(kpi.periods)}</dd>
            <dt>{t("catalog.mapLevels")}</dt>
            <dd>{kpi.map_levels.length ? kpi.map_levels.map(level).join(" · ") : "—"}</dd>
            <dt>{t("catalog.license")}</dt>
            <dd>{kpi.source.license_id ?? "—"}</dd>
            {releaseId ? (
              <>
                <dt>{t("catalog.version")}</dt>
                <dd className="mono">{releaseId.slice(0, 8)}</dd>
              </>
            ) : null}
          </dl>
        </div>
      ) : null}
    </div>
  );
}

function PlannedRow({ item, open, onToggle }: { item: CatalogPlanned; open: boolean; onToggle: () => void }) {
  const t = useTranslations();
  const { planned } = item;
  const detail = `detalhe-${planned.kpi_id}`;
  return (
    <div className={open ? "about-item open planned" : "about-item planned"}>
      <button type="button" className="about-row" aria-expanded={open} aria-controls={detail} onClick={onToggle}>
        <span className="about-name">
          <strong>{planned.label}</strong>
          <span>{item.subthemeLabel || item.themeLabel}</span>
        </span>
        <span className="about-table-id">{planned.source_table_id}</span>
        <span>
          <span className="status pending">{t("catalog.planned")}</span>
        </span>
        <span>—</span>
        <span>—</span>
        <span aria-hidden="true">
          <Chevron open={open} small />
        </span>
      </button>
      {open ? (
        <div id={detail} className="about-detail">
          <div>
            <p>{t("catalog.plannedNote", { table: planned.source_table_id, survey: planned.survey })}</p>
            {planned.note ? <p className="muted">{planned.note}</p> : null}
            <div className="about-actions">
              <a className="btn-outline" href={`${SIDRA_TABLE_URL}${planned.source_table_id}`} target="_blank" rel="noopener noreferrer">
                {t("about.tableAtSource", { id: planned.source_table_id })}
              </a>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Stat({ value, label, tone }: { value: number; label: string; tone?: "ok" | "link" | "muted" }) {
  return (
    <div className={tone ? `about-stat ${tone}` : "about-stat"}>
      <strong>{value.toLocaleString("pt-BR")}</strong>
      <span>{label}</span>
    </div>
  );
}

function Chevron({ open, small = false }: { open: boolean; small?: boolean }) {
  const s = small ? 14 : 16;
  return (
    <svg className="chevron" width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ transform: open ? "rotate(180deg)" : "none" }}>
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}
