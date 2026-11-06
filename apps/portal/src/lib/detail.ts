// Árvore do tooltip (sub-KPIs aninhados) achatada em linhas, na ordem de exibição.
import type { DetailNode } from "./types";

export interface DetailRow {
  key: string;
  label: string;
  depth: number;
  value: number | null;
  status: string;
  share: number | null;
}

export function flattenDetail(root: DetailNode): DetailRow[] {
  const rows: DetailRow[] = [];
  const visit = (node: DetailNode, depth: number, path: string) => {
    rows.push({
      key: path,
      label: node.label,
      depth,
      value: node.value ?? null,
      status: node.status,
      share: node.share_pct ?? null,
    });
    for (const child of node.children ?? []) {
      visit(child, depth + 1, `${path}|${child.category_key ?? child.label}`);
    }
  };
  visit(root, 0, "total");
  return rows;
}
