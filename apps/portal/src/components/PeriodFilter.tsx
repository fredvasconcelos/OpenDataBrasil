"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { formatPeriod } from "@/lib/format";
import { parsePeriod } from "@/lib/period";

// Filtro de Período em árvore (ADR-0026, DS 2.6): Ano › Semestre › Trimestre › Mês até o
// grão de "Período por", com caixas como em "Detalhar por". Marcar um nó marca todas as
// folhas dele (estado parcial "−" quando só algumas). Clicar no nome escolhe só aquele
// período (troca rápida, como na lista antiga). A seleção são as folhas, em ordem; vazia,
// o painel usa o padrão (o último período completo).

export interface PeriodNode {
  code: string;
  leaves: string[];
  children: PeriodNode[];
}

const PARTS = { year: 1, semester: 2, quarter: 4, month: 12 } as const;

/** Árvore das folhas (mais recentes primeiro): anos e, abaixo, semestres, trimestres e meses. */
export function buildPeriodTree(leaves: readonly string[]): PeriodNode[] {
  const info = leaves
    .map((code) => ({ code, p: parsePeriod(code) }))
    .filter((x): x is { code: string; p: NonNullable<ReturnType<typeof parsePeriod>> } => x.p !== null);
  if (!info.length) return [];
  const gran = info[0]!.p.granularity;
  const parts = PARTS[gran];
  // Posição da folha no ano (0..parts-1) → semestre e trimestre que a contêm.
  const keyAt = (level: "year" | "semester" | "quarter", year: number, index: number): string => {
    if (level === "year") return String(year);
    if (level === "semester") return `${year}S${Math.floor((index * 2) / parts) + 1}`;
    return `${year}T${Math.floor((index * 4) / parts) + 1}`;
  };
  const chain: ("year" | "semester" | "quarter")[] =
    gran === "month" ? ["year", "semester", "quarter"] : gran === "quarter" ? ["year", "semester"] : gran === "semester" ? ["year"] : [];
  const items = info.map(({ code, p }) => ({ code, year: Math.floor(p.unit / parts), index: p.unit % parts }));

  const group = (rows: typeof items, depth: number): PeriodNode[] => {
    const level = chain[depth];
    if (!level) return rows.map((r) => ({ code: r.code, leaves: [r.code], children: [] }));
    const map = new Map<string, typeof items>();
    for (const r of rows) {
      const k = keyAt(level, r.year, r.index);
      map.set(k, [...(map.get(k) ?? []), r]);
    }
    return [...map.entries()].map(([code, rs]) => ({
      code,
      leaves: rs.map((r) => r.code),
      children: group(rs, depth + 1),
    }));
  };
  const tree = group(items, 0);
  return tree.reverse(); // anos mais recentes primeiro; dentro do ano, em ordem
}

interface Props {
  /** Folhas selecionáveis (no grão escolhido, ou anos com Isolar), em ordem. */
  leaves: string[];
  /** Folhas completas (as demais, a última em andamento, levam "(parcial)"). */
  complete: string[];
  /** Folhas marcadas. */
  selected: string[];
  onChange: (next: string[]) => void;
}

export function PeriodFilter({ leaves, complete, selected, onChange }: Props) {
  const tree = buildPeriodTree(leaves);
  // Abertos: os anos (e partes) que contêm a seleção; o botão ▸/▾ abre e fecha.
  const [open, setOpen] = useState<Set<string>>(
    () => new Set(tree.flatMap(function walk(n): string[] {
      return n.children.length && n.leaves.some((l) => selected.includes(l)) ? [n.code, ...n.children.flatMap(walk)] : [];
    })),
  );
  const set = new Set(selected);
  const toggle = (node: PeriodNode) => {
    const all = node.leaves.every((l) => set.has(l));
    const next = all ? selected.filter((l) => !node.leaves.includes(l)) : [...new Set([...selected, ...node.leaves])];
    onChange(leaves.filter((l) => next.includes(l)));
  };
  const partial = (l: string) => l === leaves.at(-1) && !complete.includes(l);
  const only = (node: PeriodNode) => onChange(node.leaves);

  return (
    <div className="period-tree">
      <ul>
        {tree.map((n) => (
          <Row key={n.code} node={n} set={set} open={open} setOpen={setOpen} toggle={toggle} only={only} partial={partial} />
        ))}
      </ul>
    </div>
  );
}

function Row({
  node,
  set,
  open,
  setOpen,
  toggle,
  only,
  partial,
}: {
  node: PeriodNode;
  set: Set<string>;
  open: Set<string>;
  setOpen: (f: (s: Set<string>) => Set<string>) => void;
  toggle: (n: PeriodNode) => void;
  only: (n: PeriodNode) => void;
  partial: (leaf: string) => boolean;
}) {
  const t = useTranslations("dashboard");
  const box = useRef<HTMLInputElement>(null);
  const marked = node.leaves.filter((l) => set.has(l)).length;
  const some = marked > 0 && marked < node.leaves.length;
  useEffect(() => {
    if (box.current) box.current.indeterminate = some;
  }, [some]);
  const isOpen = open.has(node.code);
  const listId = `periodo-${node.code}`;
  const label = formatPeriod(node.code);
  return (
    <li>
      <div className="period-row">
        <span className="check small">
          <input
            ref={box}
            type="checkbox"
            aria-label={label}
            checked={marked === node.leaves.length}
            onChange={() => toggle(node)}
          />
          <button
            type="button"
            className="period-only"
            aria-label={t("periodOnly", { period: label })}
            title={t("periodOnly", { period: label })}
            onClick={() => only(node)}
          >
            {label}
          </button>
          {node.leaves.some(partial) ? <span className="check-note">{t("partial")}</span> : null}
        </span>
        {node.children.length ? (
          <button
            type="button"
            className="dim-filter-toggle"
            aria-expanded={isOpen}
            aria-controls={listId}
            aria-label={isOpen ? t("periodHide", { period: label }) : t("periodShow", { period: label })}
            onClick={() =>
              setOpen((s) => {
                const next = new Set(s);
                if (next.has(node.code)) next.delete(node.code);
                else next.add(node.code);
                return next;
              })
            }
          >
            <span aria-hidden="true">{isOpen ? "▾" : "▸"}</span>
          </button>
        ) : null}
      </div>
      {node.children.length && isOpen ? (
        <ul id={listId}>
          {node.children.map((c) => (
            <Row key={c.code} node={c} set={set} open={open} setOpen={setOpen} toggle={toggle} only={only} partial={partial} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
