"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { useValueLabels } from "@/components/useValueLabels";
import { pathTo, viewsText, type RankNode } from "@/lib/metrics";

interface Props {
  nodes: readonly RankNode[];
  selected: string | null;
  onSelect: (key: string) => void;
}

// Ranking de acessos em árvore (DS 2.12): País › Grande Região › Estado. Cada nó com
// filhos tem um botão de abrir/fechar com aria-expanded; o nome é outro botão, que leva
// o mapa até o lugar. A linha ativa tem a barra de 3px e o fundo selecionado. Quando o
// lugar é escolhido no mapa, a árvore abre o caminho até ele. Tudo pelo teclado (Tab,
// Enter e Espaço), como alternativa ao mapa.
export function AccessRanking({ nodes, selected, onSelect }: Props) {
  const t = useTranslations("metrics.ranking");
  const labels = useValueLabels();
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set(["pais:BR"]));

  // Abre os ancestrais do lugar escolhido (ajuste durante a renderização, sem efeito).
  const [seen, setSeen] = useState<string | null>(null);
  if (selected !== seen) {
    setSeen(selected);
    const ancestors = selected ? pathTo(nodes, selected).slice(0, -1) : [];
    if (ancestors.some((k) => !open.has(k))) setOpen(new Set([...open, ...ancestors]));
  }

  const toggle = (key: string) => {
    const next = new Set(open);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setOpen(next);
  };

  const render = (list: readonly RankNode[], depth: number) => (
    <ol className={depth ? "rank-children" : "access-ranking"}>
      {list.map((n, i) => {
        const expanded = open.has(n.key);
        const active = n.key === selected;
        return (
          <li key={n.key}>
            <div className={active ? "rank-row is-active" : "rank-row"} style={{ paddingLeft: depth * 18 }}>
              {n.children.length ? (
                <button
                  type="button"
                  className="rank-toggle"
                  aria-expanded={expanded}
                  aria-label={t(expanded ? "collapse" : "expand", { name: n.name })}
                  onClick={() => toggle(n.key)}
                >
                  <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
                </button>
              ) : (
                <span className="rank-toggle-space" aria-hidden="true" />
              )}
              <button type="button" className="rank-select" aria-current={active ? "true" : undefined} onClick={() => onSelect(n.key)}>
                <span className="rank-pos">{i + 1}</span>
                <span className="rank-name">{n.name}</span>
                <span className="rank-value">{viewsText(n.item, labels)}</span>
              </button>
            </div>
            {n.children.length && expanded ? render(n.children, depth + 1) : null}
          </li>
        );
      })}
    </ol>
  );

  return render(nodes, 0);
}
