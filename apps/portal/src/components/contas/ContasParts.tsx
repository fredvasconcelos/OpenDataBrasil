"use client";

// Peças do Painel das contas (ADR-0039, seção 4): destaques, composição, ranking, situação
// do período e estados. Tudo é apresentação: os números vêm prontos da API.
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { CSSProperties, ReactNode } from "react";

import { FaIcon } from "@/components/FaIcon";
import { periodAlerts } from "@/lib/contas/adapt";
import { brl, brlShort, periodLabel, seat, share } from "@/lib/contas/format";
import type { ContasProvenance, ContasRanking, ContasTable } from "@/lib/contas/types";
import { classIcon, functionVisual } from "@/lib/contas/visual";
import { FA } from "@/lib/faIcons";
import { themeStyle } from "@/lib/themes";

const TYPE_CONSTITUTIONAL = "Constitucionais e Royalties";
const TYPE_LEGAL = "Legais, Voluntárias e Específicas";

/** Quanto: total do território e a divisão por tipo, como a API entrega. */
export function ContasHighlights({ total, byType }: {
  total: number;
  byType: ContasTable;
}) {
  const t = useTranslations("contas.highlights");
  const types = [
    { key: "constitutional", code: TYPE_CONSTITUTIONAL },
    { key: "legal", code: TYPE_LEGAL },
  ];
  return (
    <ul className="contas-highlights">
      <li className="contas-kpi is-main">
        <span className="contas-kpi-label">{t("total")}</span>
        <span className="contas-kpi-value">{brlShort(total)}</span>
        <span className="contas-kpi-note">{brl(total)}</span>
      </li>
      {types.map(({ key, code }) => {
        const value = byType.rows.find((r) => r.key === code)?.value;
        return <li key={key} className="contas-kpi">
          <span className="contas-kpi-label">{t(key)}</span>
          <span className="contas-kpi-value">{value === undefined ? "—" : brlShort(value)}</span>
          <span className="contas-kpi-note">{value === undefined ? t("noRecords") : brl(value)}</span>
        </li>;
      })}
      {["applied", "appliedShare"].map((key) => <li key={key} className="contas-kpi is-unavailable">
        <span className="contas-kpi-label">{t(key)}</span>
        <span className="contas-kpi-value">—</span>
        <span className="contas-kpi-note">{t("unavailable")}</span>
        <details className="contas-method-note"><summary>{t("whyUnavailable")}</summary><p>{t("applicationNote")}</p></details>
      </li>)}
    </ul>
  );
}

function Bar({ label, value, width, note, icon, style, pressed, onClick }: {
  label: string;
  value: number;
  width: number;
  note?: string;
  icon?: ReactNode;
  style?: CSSProperties;
  pressed?: boolean;
  onClick?: () => void;
}) {
  const body = (
    <>
      <span className="contas-bar-head">
        {icon ? <span className="contas-area-icon" aria-hidden="true">{icon}</span> : null}
        <span className="contas-bar-label">{label}</span>
        <span className="contas-bar-value">{brlShort(value)}</span>
        {note ? <span className="contas-bar-share">{note}</span> : null}
      </span>
      <span className="contas-bar-track" aria-hidden="true">
        <span style={{ width: `${Math.max(width * 100, 0.6)}%` }} />
      </span>
    </>
  );
  return (
    <li style={style}>
      {onClick ? (
        <button type="button" className="contas-bar" aria-pressed={pressed} onClick={onClick}>{body}</button>
      ) : (
        <div className="contas-bar">{body}</div>
      )}
    </li>
  );
}

/** Como: tipos no recorte selecionado e todas as áreas do território no período. */
export function ContasComposition({ byType, composition, area, onArea }: {
  byType: ContasTable;
  composition: ContasTable;
  area?: string | null;
  onArea?: (code: string) => void;
}) {
  const t = useTranslations("contas.how");
  const types = byType.rows;
  // Largura relativa à maior barra de cada lista: só desenho, não é dado novo.
  const maxType = Math.max(...types.map((r) => r.value), 1);
  const maxArea = Math.max(...composition.rows.map((r) => r.value), 1);
  return (
    <div className="contas-how">
      <section aria-labelledby="como-tipo">
        <h3 id="como-tipo">{t("byType")}</h3>
        <ul className="contas-bars">
          {types.map((r) => (
            <Bar key={r.key} label={r.label} value={r.value} width={r.value / maxType} note={share(r.share)} />
          ))}
        </ul>
      </section>
      <section className="contas-areas" aria-labelledby="como-area">
        <h3 id="como-area">{t("byArea")}</h3>
        <ul className="contas-bars contas-area-scroll" tabIndex={0} aria-labelledby="como-area">
          {composition.rows.map((r) => {
            const v = functionVisual(r.key);
            return (
              <Bar
                key={r.key}
                label={r.label}
                value={r.value}
                width={r.value / maxArea}
                note={share(r.share)}
                icon={<FaIcon icon={v.icon} size={13} />}
                style={themeStyle(v.family)}
                pressed={area === r.key}
                onClick={onArea ? () => onArea(r.key) : undefined}
              />
            );
          })}
        </ul>
        {onArea ? <p className="contas-hint">{t("areaHint")}</p> : null}
      </section>
    </div>
  );
}

/** Quem mais recebeu: ranking da lente A. Na lista, só nome, sede, classe e valor. */
export function ContasRankingTable({ ranking, hrefOf, onPage }: { ranking: ContasRanking; hrefOf?: (id: string) => string; onPage?: (page: number) => void }) {
  const t = useTranslations("contas.who");
  return (
    <div className="contas-ranking">
      <table className="contas-table">
        <thead>
          <tr>
            <th scope="col" className="num">{t("rank")}</th>
            <th scope="col">{t("name")}</th>
            <th scope="col">{t("seat")}</th>
            <th scope="col">{t("class")}</th>
            <th scope="col" className="num">{t("value")}</th>
          </tr>
        </thead>
        <tbody>
          {ranking.rows.map((r) => (
            <tr key={r.recipient.recipient_id}>
              <td className="num rank" data-l={t("rank")}>{r.rank}º</td>
              <td data-l={t("name")}>
                {hrefOf ? <Link href={hrefOf(r.recipient.recipient_id)}>{r.recipient.name ?? "—"}</Link> : r.recipient.name ?? "—"}
              </td>
              <td data-l={t("seat")}>{seat(r.recipient.seat_municipality, r.recipient.seat_uf)}</td>
              <td data-l={t("class")}>
                <span className="contas-class">
                  <FaIcon icon={classIcon(r.recipient.recipient_class)} size={13} />
                  {r.recipient.class_label}
                </span>
              </td>
              <td className="num" data-l={t("value")}>{brl(r.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="contas-ranking-foot">
        <span>{t("count", { count: ranking.total_recipients.toLocaleString("pt-BR") })}</span>
        <span className="contas-pager">
          <button type="button" disabled={!onPage || ranking.page <= 1} aria-label={t("previous")} onClick={() => onPage?.(ranking.page - 1)}>‹</button>
          {t("page", { page: ranking.page, pages: ranking.pages })}
          <button type="button" disabled={!onPage || ranking.page >= ranking.pages} aria-label={t("next")} onClick={() => onPage?.(ranking.page + 1)}>›</button>
        </span>
      </div>
      <p className="contas-hint">{t("note")}</p>
      {ranking.total_recipients > ranking.pages * ranking.page_size ? <p className="contas-hint">{t("limit", { count: (ranking.pages * ranking.page_size).toLocaleString("pt-BR") })}</p> : null}
    </div>
  );
}

/** Situação do período: fechado, ou os meses abertos e incompletos que a API sinaliza. */
export function PeriodStatusList({ provenance }: { provenance: ContasProvenance }) {
  const t = useTranslations("contas.status");
  const alerts = periodAlerts(provenance.period_notes);
  if (!alerts.length) {
    return <span className="period-badge is-closed"><FaIcon icon={FA.registro} size={12} />{t("closed")}</span>;
  }
  return (
    <ul className="period-alerts">
      {alerts.map((n) => (
        <li key={n.period} className={`period-badge is-${n.status === "aberto" ? "open" : "incomplete"}`} title={n.note}>
          <FaIcon icon={n.status === "aberto" ? FA.transferidos : FA.semInformacao} size={12} />
          <strong>{periodLabel(n.period)}</strong> {n.status === "aberto" ? t("open") : t("incomplete")}
        </li>
      ))}
    </ul>
  );
}

/** Tooltip do mapa das contas: a mesma estrutura do DetailTooltip, com o conteúdo do bloco 2. */
export function ContasTooltip({ name, value, shareOfTotal, period, inline = false }: {
  name: string;
  value: number;
  shareOfTotal?: number | null;
  period: string;
  inline?: boolean;
}) {
  const t = useTranslations("contas");
  return (
    <div className={inline ? "tooltip tooltip-inline" : "tooltip"} role="tooltip">
      <div className="tt-stripe" aria-hidden="true"><span /><span /><span /></div>
      <div className="tt-body">
        <div className="tt-head">
          <span className="tt-name">{name}</span>
          <span className="tt-period">{period}</span>
        </div>
        <div className="tt-total">
          <span className="tt-total-value">{brlShort(value)}</span>
          {shareOfTotal !== undefined && shareOfTotal !== null ? <span className="tt-total-share">{share(shareOfTotal)}</span> : null}
        </div>
        <p className="tt-full">{brl(value)}</p>
        <p className="tt-lens"><FaIcon icon={FA.transferidos} size={12} />{t("lensName")} · {t("source").split(".")[0]}</p>
      </div>
    </div>
  );
}

/** 503 do bloco 2: só as contas ficam fora; as Estatísticas oficiais seguem. */
export function ContasUnavailable({ onRetry }: { onRetry?: () => void }) {
  const t = useTranslations("contas.unavailable");
  return (
    <div className="contas-state is-error" role="alert">
      <span className="contas-state-icon" aria-hidden="true"><FaIcon icon={FA.contas} size={28} /></span>
      <h2>{t("title")}</h2>
      <p>{t("text")}</p>
      <div className="contas-state-actions">
        <button type="button" className="btn-primary" onClick={() => onRetry ? onRetry() : window.location.reload()}>{t("retry")}</button>
        <Link href="/estatisticas/painel" className="btn-outline">{t("goStats")}</Link>
      </div>
    </div>
  );
}

/** Recorte sem valor: a API respondeu com rows vazias e total 0. */
export function ContasEmpty() {
  const t = useTranslations("contas.empty");
  return (
    <div className="contas-state" role="status">
      <span className="contas-state-icon" aria-hidden="true"><FaIcon icon={FA.semInformacao} size={28} /></span>
      <h2>{t("title")}</h2>
      <p>{t("text")}</p>
    </div>
  );
}
