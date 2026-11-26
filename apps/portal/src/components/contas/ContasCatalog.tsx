"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useState } from "react";

import { FaIcon } from "@/components/FaIcon";
import { SearchGlyph } from "@/components/HomeCatalog";
import { contasApi } from "@/lib/api/contas";
import { defaultPeriod } from "@/lib/contas/state";
import { FA, type FaDef } from "@/lib/faIcons";
import { normalize, themeStyle, type ThemeFamily } from "@/lib/themes";
import { useAsync } from "@/lib/useAsync";

const SAMPLE = 4;
const PANEL = "/contas/painel";
// Os mesmos nomes dos cartões do painel; um tipo novo da fonte aparece com o rótulo da API.
const TYPE_LABELS: Record<string, "constitutional" | "legal"> = {
  "Constitucionais e Royalties": "constitutional",
  "Legais, Voluntárias e Específicas": "legal",
};

interface Item {
  id: string;
  label: string;
  href: string;
  /** Termos extras da busca (siglas e nomes populares), nunca exibidos. */
  terms?: string;
}

interface Group {
  id: "visao" | "tipos" | "areas" | "recebimentos" | "execucao";
  label: string;
  note: string;
  icon: FaDef;
  family: ThemeFamily;
  terms: string;
  items: Item[];
}

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
  const loaded = useAsync(async () => {
    const meta = await contasApi.meta();
    const period = defaultPeriod(meta);
    const [areas, types] = await Promise.all([
      contasApi.areas("brasil:1", [period]),
      contasApi.table({ geography_key: "brasil:1", periods: [period], group_by: "transfer_type" }),
    ]);
    return { meta, period, areas: areas.rows, types: types.rows };
  }, [], retry);

  const groups: Group[] = loaded.data
    ? [
        {
          id: "visao",
          label: c("groups.visao.name"),
          note: c("groups.visao.note"),
          icon: FA.contas,
          family: "azul",
          terms: c("groups.visao.terms"),
          items: [
            { id: "total", label: c("items.total"), href: PANEL },
            { id: "onde", label: c("items.onde"), href: `${PANEL}#onde`, terms: c("items.ondeTerms") },
            { id: "quando", label: c("items.quando"), href: `${PANEL}#quando` },
            { id: "quem", label: c("items.quem"), href: `${PANEL}#quem`, terms: c("items.quemTerms") },
          ],
        },
        {
          id: "tipos",
          label: c("groups.tipos.name"),
          note: c("groups.tipos.note"),
          icon: FA.transferidos,
          family: "petroleo",
          terms: c("groups.tipos.terms"),
          items: loaded.data.types.map((r) => ({ id: r.key, label: TYPE_LABELS[r.key] ? t(`contas.highlights.${TYPE_LABELS[r.key]}`) : r.label, href: `${PANEL}#como`, terms: TYPE_LABELS[r.key] ? c(`items.${TYPE_LABELS[r.key]}Terms`) : undefined })),
        },
        {
          id: "areas",
          label: c("groups.areas.name"),
          note: c("groups.areas.note", { year: loaded.data.period.slice(0, 4) }),
          icon: FA.gestao,
          family: "roxo",
          terms: c("groups.areas.terms"),
          items: loaded.data.areas.map((r) => ({ id: r.key, label: r.label, href: `${PANEL}?${new URLSearchParams({ area: r.key })}` })),
        },
        {
          id: "recebimentos", label: t("contas.federal.B"), note: t("contas.federal.receiptsNote"),
          icon: FA.recebimento, family: "petroleo", terms: "favorecido pagamento sede estado município CNAE órgão",
          items: [{ id: "pagamentos", label: t("contas.federal.B"), href: `${PANEL}?lens=B` }],
        },
        {
          id: "execucao", label: t("contas.federal.C"), note: t("contas.federal.noSum"),
          icon: FA.gestao, family: "roxo", terms: "execução empenhado liquidado pago restos pagar orçamento",
          items: ["committed", "liquidated", "paid", "payables_registered", "payables_cancelled", "payables_paid"].map((phase) => ({ id: phase, label: t(`contas.federal.phases.${phase}`), href: `${PANEL}?lens=C#fase-${phase}` })),
        },
      ].filter((g) => g.id !== "recebimentos" && g.id !== "execucao" || loaded.data?.meta.lenses.some((l) => l.lens === (g.id === "recebimentos" ? "B" : "C"))) as Group[]
    : [];

  const query = normalize(q.trim());
  const matches = (g: Group, it: Item) => !query || normalize(`${it.label} ${it.terms ?? ""} ${g.label} ${g.terms}`).includes(query);
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
