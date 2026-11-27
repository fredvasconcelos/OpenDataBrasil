import { FA } from "@/lib/faIcons";

// Compartilhado por componentes de servidor e navegador, sem fronteira "use client".
export const BLOCKS = [
  { id: "estatisticas", href: "/estatisticas/painel", icon: FA.estatisticas },
  { id: "contas", href: "/contas/painel", icon: FA.contas },
] as const;

export type BlockId = (typeof BLOCKS)[number]["id"];

/** Bloco da rota atual, incluindo os links antigos das Estatísticas. */
export function blockOf(path: string): BlockId | null {
  if (path.startsWith("/contas")) return "contas";
  if (path.startsWith("/estatisticas") || path.startsWith("/dashboard")) return "estatisticas";
  return null;
}
