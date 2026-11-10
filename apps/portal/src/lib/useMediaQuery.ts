"use client";

import { useSyncExternalStore } from "react";

// Media query no cliente (no servidor devolve `serverValue`).
// Usado para o layout de tela cheia (≥ 1600 px) do painel.
export const WIDE_QUERY = "(min-width: 1600px)";

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
