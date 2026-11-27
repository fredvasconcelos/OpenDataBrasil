"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useState } from "react";

import { FaIcon } from "@/components/FaIcon";
import { SearchGlyph } from "@/components/HomeCatalog";
import { FA, type FaDef } from "@/lib/faIcons";
import { normalize, themeStyle } from "@/lib/themes";
import { contasGroups, loadContasCatalog, matchContas, type Group, type Item } from "@/lib/contas/catalog";
import { useAsync } from "@/lib/useAsync";

const SAMPLE = 4;
// Catálogo das Contas públicas no molde do catálogo das Estatísticas (DS ODBr): busca
// com lupa, etiquetas de grupo, grade de cartões em "Todos" e lista completa ao escolher
// um grupo ou buscar. Cada item abre o painel da lente correspondente. Tipos e
// áreas vêm da API (release vigente); só a área filtra o painel, os tipos levam à
// distribuição, onde aparecem lado a lado.
export function ContasCatalog() {
  const t = useTranslations();
  const c = useTranslations("contas.catalog");
  const [retry, setRetry] = useState(0);
  const [q, setQ] = useState("");
  const [group, setGroup] = useState<Group["id"] | "all">("all");
  const loaded = useAsync(loadContasCatalog, [], retry);
  const groups = contasGroups(loaded.data, t);

  const query = normalize(q.trim());
  const matches = (g: Group, it: Item) => matchContas(g, it, query);
  const listed = groups
    .filter((g) => group === "all" || g.id === group)
    .map((g) => ({ ...g, found: g.items.filter((it) => matches(g, it)) }))
    .filter((g) => g.found.length > 0);
  const total = groups.reduce((n, g) => n + g.items.length, 0);
  const found = listed.reduce((n, g) => n + g.found.length, 0);
  const grid = group === "all" && !query;

  return (
    <>
      <section className="home-hero">
        <div role="search" className="home-search">
          <label htmlFor="contas-busca">{c("search")}</label>
          <SearchGlyph />
          <input id="contas-busca" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={c("placeholder")} />
          <p aria-live="polite" className="home-search-status">
            {q.trim() && loaded.data ? t("catalog.found", { count: found }) : c("hint")}
          </p>
        </div>
      </section>

      {loaded.loading ? <p role="status">{t("contas.loading")}</p> : null}
      {loaded.error ? (
        <div className="card" role="alert">
          <p>{t("contas.unavailable.text")}</p>
          <button type="button" className="btn-outline" onClick={() => setRetry((n) => n + 1)}>{t("contas.unavailable.retry")}</button>
        </div>
      ) : null}

      {loaded.data ? (
        <section className="theme-chips" aria-label={c("filterByGroup")}>
          <h2 className="eyebrow">{c("groupsTitle")}</h2>
          <div>
            <Chip on={group === "all"} label={t("catalog.all")} count={total} icon={FA.generico} onClick={() => setGroup("all")} />
            {groups.map((g) => (
              <Chip key={g.id} on={group === g.id} label={g.label} count={g.items.length} icon={g.icon} style={themeStyle(g.family)} onClick={() => setGroup(g.id)} />
            ))}
          </div>
        </section>
      ) : null}

      {!loaded.data ? null : grid ? (
        <div className="theme-grid">
          {groups.map((g) => (
            <section key={g.id} className="theme-card" aria-labelledby={`contas-grupo-${g.id}`} style={themeStyle(g.family)}>
              <div className="theme-card-head">
                <GroupIcon icon={g.icon} />
                <div>
                  <h2 id={`contas-grupo-${g.id}`}>{g.label}</h2>
                  <span>{t("catalog.kpiCount", { count: g.items.length })}</span>
                </div>
              </div>
              <ItemList items={g.items.slice(0, SAMPLE)} />
              <div className="theme-card-foot">
                <button type="button" className="text-btn" onClick={() => setGroup(g.id)}>
                  {g.items.length > SAMPLE ? t("catalog.seeAll", { count: g.items.length }) : c("seeGroup")}
                </button>
              </div>
            </section>
          ))}
        </div>
      ) : listed.length ? (
        listed.map((g) => (
          <section key={g.id} className="theme-panel" aria-labelledby={`contas-lista-${g.id}`} style={themeStyle(g.family)}>
            <div className="theme-panel-head">
              <GroupIcon icon={g.icon} size={24} box={46} />
              <div>
                <h2 id={`contas-lista-${g.id}`}>{g.label}</h2>
                <span>{t("catalog.kpiCount", { count: g.found.length })} · {g.note}</span>
              </div>
            </div>
            {/* Sem subtemas: a própria lista flui pelas colunas do painel. */}
            <div className="theme-panel-cols">
              <ItemList items={g.found} />
            </div>
          </section>
        ))
      ) : (
        <p className="empty">{c("empty")}</p>
      )}
    </>
  );
}

function ItemList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map((it) => (
        <li key={it.id}>
          <Link className="kpi-link" href={it.href}>
            {it.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function GroupIcon({ icon, size = 20, box = 40 }: { icon: FaDef; size?: number; box?: number }) {
  return (
    <span className="theme-icon" style={{ width: box, height: box }} aria-hidden="true">
      <FaIcon icon={icon} size={size} />
    </span>
  );
}

function Chip({ on, label, count, icon, style, onClick }: { on: boolean; label: string; count: number; icon: FaDef; style?: CSSProperties; onClick: () => void }) {
  return (
    <button type="button" className="theme-chip" aria-pressed={on} onClick={onClick} style={style}>
      <span className="theme-chip-icon" aria-hidden="true">
        <FaIcon icon={icon} size={14} />
      </span>
      {label}
      <span className="theme-chip-count">{count}</span>
    </button>
  );
}
