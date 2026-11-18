"use client";

import { useSyncExternalStore } from "react";

// Media query no cliente (no servidor devolve `serverValue`).
// Usado para o layout de tela cheia (≥ 1600 px) do painel.
export const WIDE_QUERY = "(min-width: 1600px)";
// Versão mobile do painel (DS v2.5): painel inferior e abas até 899 px.
export const MOBILE_QUERY = "(max-width: 899px)";
// Tela de toque sem mouse: sem tooltip por hover; o toque seleciona e mostra o cartão.
export const COARSE_QUERY = "(hover: none) and (pointer: coarse)";

export function useMediaQuery(query: string, serverValue = false): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const media = window.matchMedia(query);
      media.addEventListener("change", onChange);
      return () => media.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => serverValue,
  );
}
