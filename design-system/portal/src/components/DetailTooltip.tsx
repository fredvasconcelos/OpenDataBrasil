"use client";

import { useTranslations } from "next-intl";

import { formatShare, formatValue, unitSuffix } from "@/lib/format";
import { SERIES } from "@/lib/theme";
import type { Detail, DetailNode } from "@/lib/types";

interface Props {
  name: string;
  detail: Detail | null;
  loading: boolean;
  x: number;
  y: number;
}

// Tooltip do mapa (Design System ODBr): só o território sob o ponteiro, com os sub-KPIs
// das dimensões marcadas em "Detalhar por", na ordem de dimension_order
// (ex.: cor ou raça > sexo). Cada percentual é sobre o nó de cima (share_pct da API).
// Três formas, escolhidas pelos dados:
//   1. Categorias (ex.: só cor ou raça): barra de composição + uma barra por categoria.
//   2. Categorias > sexo: idem, com a divisão homens/mulheres sob cada categoria.
//   3. Só sexo: pictograma de 10 figuras + barra dividida + números grandes.
// Outros segundos níveis viram uma lista curta sob a categoria.

const WIDTH = 340;
const MALE = "M8.6 8.2h6.8a1.6 1.6 0 011.6 1.6V15h-2.3v7h-6.4v-7H7V9.8a1.6 1.6 0 011.6-1.6z";
const FEMALE = "M9.6 8.2h4.8l3.4 8.6h-3.1V22h-5.4v-5.2H6.2z";
const MEN = "var(--odbr-series-1)";
const WOMEN = "var(--odbr-series-2)";

type Sex = "m" | "f";

function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();
}

function sexOf(node: DetailNode): Sex | null {
  const l = normalize(node.label);
  if (l.startsWith("homem") || l.startsWith("homens") || l === "masculino") return "m";
  if (l.startsWith("mulher") || l === "feminino") return "f";
  return null;
}

function sexPair(nodes: readonly DetailNode[]): [DetailNode, DetailNode] | null {
  if (nodes.length !== 2) return null;
  const m = nodes.find((n) => sexOf(n) === "m");
  const f = nodes.find((n) => sexOf(n) === "f");
  return m && f ? [m, f] : null;
}

const childrenOf = (node: DetailNode): DetailNode[] => node.children ?? [];
const clamp = (share: number | null | undefined) => (share === null || share === undefined ? 0 : Math.max(0, Math.min(100, share)));
const byValue = (a: DetailNode, b: DetailNode) => (b.value ?? -Infinity) - (a.value ?? -Infinity);
const shareOrValue = (n: DetailNode) => (n.value === null ? formatValue(n.value, n.status) : formatShare(n.share_pct));
const keyOf = (n: DetailNode) => n.category_key ?? n.label;

function hasShare(node: DetailNode): boolean {
  return node.share_pct !== null || childrenOf(node).some(hasShare);
}

/** Parte dos homens na barra dividida, mesmo se um dos lados estiver sob sigilo. */
function menShare(m: DetailNode, f: DetailNode): number {
  if (m.share_pct !== null) return clamp(m.share_pct);
  if (f.share_pct !== null) return 100 - clamp(f.share_pct);
  return 50;
}

function Figure({ sex, size = 13, color }: { sex: Sex; size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" style={color ? { fill: color } : undefined}>
      <circle cx="12" cy="4" r="2.6" />
      <path d={sex === "m" ? MALE : FEMALE} />
    </svg>
  );
}

function PairLine({ pair, color }: { pair: [DetailNode, DetailNode]; color: string }) {
  const [m, f] = pair;
  return (
    <div className="tt-pair">
      <span className="tt-pair-side">
        <Figure sex="m" />
        <span className="sr-only">{m.label} </span>
        {shareOrValue(m)}
      </span>
      <span className="tt-pair-bar" aria-hidden="true">
        <span style={{ width: `${menShare(m, f)}%`, background: color }} />
        <span className="rest" style={{ background: color }} />
      </span>
      <span className="tt-pair-side end">
        {shareOrValue(f)}
        <span className="sr-only"> {f.label}</span>
        <Figure sex="f" />
      </span>
    </div>
  );
}

function SubList({ nodes }: { nodes: DetailNode[] }) {
  return (
    <ul className="tt-sub">
      {nodes.map((n) => (
        <li key={keyOf(n)}>
          <span>{n.label}</span>
          <span>{formatValue(n.value, n.status)}</span>
          <span>{formatShare(n.share_pct)}</span>
        </li>
      ))}
    </ul>
  );
}

function Categories({ nodes }: { nodes: DetailNode[] }) {
  const sorted = [...nodes].sort(byValue);
  const firstPair = sorted.map((n) => sexPair(childrenOf(n))).find(Boolean) ?? null;
  return (
    <>
      <div className="tt-stack" aria-hidden="true">
        {sorted.map((n, i) => (
          <span key={keyOf(n)} style={{ width: `${clamp(n.share_pct)}%`, background: SERIES[i % SERIES.length] }} />
        ))}
      </div>
      {firstPair ? (
        <div className="tt-legend" aria-hidden="true">
          <span>
            <Figure sex="m" size={14} color="var(--odbr-text-muted)" />
            <span className="tt-swatch" />
            {firstPair[0].label}
          </span>
          <span>
            <Figure sex="f" size={14} color="var(--odbr-text-muted)" />
            <span className="tt-swatch light" />
            {firstPair[1].label}
          </span>
        </div>
      ) : null}
      <ul className="tt-list">
        {sorted.map((n, i) => {
          const color = SERIES[i % SERIES.length] as string;
          const kids = childrenOf(n);
          const pair = sexPair(kids);
          return (
            <li key={keyOf(n)} className="tt-item">
              <div className="tt-row">
                <span className="tt-dot" style={{ background: color }} aria-hidden="true" />
                <span className="tt-label">{n.label}</span>
                <span className="tt-value">{formatValue(n.value, n.status)}</span>
                <span className="tt-share">{formatShare(n.share_pct)}</span>
              </div>
              <div className="tt-bar" aria-hidden="true">
                <span style={{ width: `${clamp(n.share_pct)}%`, background: color }} />
              </div>
              {pair ? <PairLine pair={pair} color={color} /> : kids.length ? <SubList nodes={kids} /> : null}
            </li>
          );
        })}
      </ul>
    </>
  );
}

function SexOnly({ pair, note }: { pair: [DetailNode, DetailNode]; note: string }) {
  const [m, f] = pair;
  const share = menShare(m, f);
  const known = m.share_pct !== null || f.share_pct !== null;
  const menFigures = Math.round(share / 10);
  return (
    <>
      {known ? (
        <>
          <div className="tt-figures" role="img" aria-label={`${m.label} ${shareOrValue(m)}, ${f.label} ${shareOrValue(f)}`}>
            {Array.from({ length: 10 }, (_, i) =>
              i < menFigures ? <Figure key={i} sex="m" size={26} color={MEN} /> : <Figure key={i} sex="f" size={26} color={WOMEN} />,
            )}
          </div>
          <div className="tt-split" aria-hidden="true">
            <span style={{ width: `${share}%`, background: MEN }} />
            <span style={{ background: WOMEN }} />
          </div>
        </>
      ) : null}
      <div className="tt-sexes">
        <div>
          <span className="tt-sex-label">
            <span className="tt-dot" style={{ background: MEN }} aria-hidden="true" />
            {m.label}
          </span>
          <span className="tt-sex-share" style={{ color: MEN }}>
            {shareOrValue(m)}
          </span>
          <span className="tt-sex-value">{formatValue(m.value, m.status)}</span>
        </div>
        <div className="end">
          <span className="tt-sex-label">
            {f.label}
            <span className="tt-dot" style={{ background: WOMEN }} aria-hidden="true" />
          </span>
          <span className="tt-sex-share" style={{ color: WOMEN }}>
            {shareOrValue(f)}
          </span>
          <span className="tt-sex-value">{formatValue(f.value, f.status)}</span>
        </div>
      </div>
      {known ? <p className="tt-caption">{note}</p> : null}
    </>
  );
}

export function DetailTooltip({ name, detail, loading, x, y }: Props) {
  const t = useTranslations("dashboard");
  const vw = typeof window !== "undefined" ? window.innerWidth : 1280;
  const vh = typeof window !== "undefined" ? window.innerHeight : 800;
  const left = Math.max(12, x > vw - (WIDTH + 40) ? x - WIDTH - 16 : x + 16);
  // Na metade de baixo da tela, o tooltip abre para cima do ponteiro.
  const style = y > vh * 0.55 ? { left, top: y - 12, transform: "translateY(-100%)" } : { left, top: y + 12 };

  const root = detail?.root ?? null;
  const kids = root ? childrenOf(root) : [];
  const onlySex = sexPair(kids);

  return (
    <div className="tooltip" role="tooltip" style={style}>
      <div className="tt-stripe" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="tt-body">
        <div className="tt-head">
          <span className="tt-name">{name}</span>
          {detail ? <span className="tt-period">{detail.period}</span> : null}
        </div>
        {loading && !detail ? (
          <div className="tt-loading" aria-busy="true">
            <span className="skeleton" />
            <span className="skeleton short" />
            <span className="muted small">{t("loading")}</span>
          </div>
        ) : null}
        {detail && root ? (
          <>
            <div className="tt-total">
              <span className="tt-total-value">{formatValue(root.value, root.status)}</span>
              <span className="tt-unit">{unitSuffix(detail.unit)}</span>
            </div>
            {onlySex ? <SexOnly pair={onlySex} note={t("figureNote")} /> : kids.length ? <Categories nodes={kids} /> : null}
            <p className="tt-note">
              {unitSuffix(detail.unit)}
              {hasShare(root) ? ` · ${t("derivedNote")}` : ""}
            </p>
          </>
        ) : null}
      </div>
    </div>
  );
}
