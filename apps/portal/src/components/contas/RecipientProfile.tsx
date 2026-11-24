"use client";

// Ficha do favorecido (ADR-0039, seção 4): as duas lentes lado a lado, nunca somadas.
// A API atual fornece só o nome: não acrescentar identificadores ausentes do contrato.
import Link from "next/link";
import { useTranslations } from "next-intl";

import { FaIcon } from "@/components/FaIcon";
import { SeriesChart } from "@/components/SeriesChart";
import { brl, brlShort, seat } from "@/lib/contas/format";
import type { RecipientProfile as Profile } from "@/lib/contas/types";
import { classIcon } from "@/lib/contas/visual";
import { FA } from "@/lib/faIcons";
import type { Series } from "@/lib/types";

const LENSES = ["A", "B"] as const;

function lensSeries(profile: Profile, lens: string, name: string, year: number): Series {
  const points = profile.series.filter((p) => p.lens === lens && p.period.startsWith(String(year)));
  return {
    kpi_id: "contas_favorecido", indicator_id: `contas_${lens}`,
    geography: { geography_key: profile.recipient.recipient_id, name, level_id: "favorecido" },
    unit: "Reais", grain: "mes",
    series: [{ key: lens, label: name, full_label: name, categories: {}, depth: 0, points: points.map((p) => ({ period: p.period, value: p.value, status: "valid" })) }],
    provenance: { release_id: profile.provenance.release_id, tables: profile.provenance.tables, derived: false, truncated: false },
  };
}

export function RecipientProfile({ profile, year }: {
  profile: Profile;
  year: number;
}) {
  const t = useTranslations("contas.profile");
  const common = useTranslations("contas");
  const r = profile.recipient;
  const totals = LENSES.map((lens) => ({ lens, total: profile.totals.find((x) => x.lens === lens && x.year === year)?.value ?? null }));
  const shown = totals.filter((x) => x.total !== null);
  return (
    <main className="page page-wide recipient-page">
      <Link href="/contas/painel" className="back-link">‹ {t("back")}</Link>
      <header className="recipient-head">
        <span className="recipient-icon" aria-hidden="true"><FaIcon icon={classIcon(r.recipient_class)} size={26} /></span>
        <div>
          <p className="crumb">{r.class_label} · {seat(r.seat_municipality, r.seat_uf)}</p>
          <h1>{r.name ?? "—"}</h1>
        </div>
        <a className="btn-outline recipient-official" href="https://portaldatransparencia.gov.br" rel="noreferrer">{t("official")}</a>
      </header>
      {r.is_natural_person ? (
        <p className="contas-notice" role="note"><FaIcon icon={FA.semInformacao} size={14} />{profile.notes[0] ?? t("homonym")}</p>
      ) : null}
      <dl className="recipient-facts">
        {profile.legal_nature ? (<div><dt>{t("nature")}</dt><dd>{profile.legal_nature}</dd></div>) : null}
        {profile.economic_activity ? (<div><dt>{t("activity")}</dt><dd>{profile.economic_activity}</dd></div>) : null}
      </dl>
      <section aria-labelledby="lentes">
        <h2 id="lentes" className="contas-section-title"><FaIcon icon={FA.transferidos} size={16} />{t("byLens", { year })}</h2>
        <ul className="recipient-lenses">
          {shown.map((x) => (
            <li key={x.lens} className="recipient-lens" data-lens={x.lens}>
              <span className="recipient-lens-name">
                <FaIcon icon={x.lens === "A" ? FA.transferidos : FA.recebimento} size={14} />
                {x.lens === "A" ? t("lensA") : t("lensB")}
              </span>
              <span className="contas-kpi-value">{brlShort(x.total as number)}</span>
              <span className="contas-kpi-note">{brl(x.total as number)}</span>
              <span className="recipient-lens-note">{x.lens === "A" ? t("lensANote") : t("lensBNote")}</span>
            </li>
          ))}
        </ul>
        {shown.length > 1 ? <p className="contas-hint">{t("notSummed")}</p> : null}
      </section>
      <div className="recipient-grid">
        {shown.map((x) => (
          <section key={x.lens} className="card">
            <h2 className="contas-section-title">{x.lens === "A" ? t("lensA") : t("lensB")} · {t("series", { year })}</h2>
            <div className="recipient-chart"><SeriesChart data={lensSeries(profile, x.lens, x.lens === "A" ? t("lensA") : t("lensB"), year)} /></div>
          </section>
        ))}
      </div>
      <p className="contas-hint">{t("officialUnavailable")}</p>
      {profile.notes.map((note) => <p key={note} className="contas-hint" role="note">{note}</p>)}
      {shown.map(({ lens }) => {
        const organs = profile.organs.filter((o) => o.lens === lens).slice(0, 10);
        return organs.length ? (
          <section key={lens} className="card" aria-labelledby={`orgaos-${lens}`}>
            <h2 id={`orgaos-${lens}`} className="contas-section-title">{t("organs")} · {lens === "A" ? t("lensA") : t("lensB")}</h2>
            <ol className="recipient-organs">{organs.map((o) => <li key={o.organ}><span>{o.organ}</span><strong>{brl(o.value)}</strong></li>)}</ol>
          </section>
        ) : null;
      })}
      <footer className="contas-profile-source">
        <p>{common("source")}</p>
        <p>{common("release")}: <code>{profile.provenance.release_id}</code></p>
        <details>
          <summary>{common("notes")}</summary>
          {profile.provenance.period_notes?.map((note) => <p key={note.period}>{note.period}: {note.note}</p>)}
          {profile.provenance.tables.map((table) => <p key={table.table_id}>{table.table_id}: {table.delta_version}</p>)}
        </details>
      </footer>
    </main>
  );
}
