"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

import { THEME_STORAGE_KEY, type ThemeName } from "@/lib/theme";

// Alterna claro/dark. Sem escolha salva, segue o sistema (prefers-color-scheme).
// O script em layout.tsx aplica o tema salvo antes da primeira pintura (sem piscar).
const DARK_QUERY = "(prefers-color-scheme: dark)";

function current(): ThemeName {
  const attr = document.documentElement.dataset.theme;
  if (attr === "light" || attr === "dark") return attr;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(DARK_QUERY);
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  media.addEventListener("change", onChange);
  return () => {
    observer.disconnect();
    media.removeEventListener("change", onChange);
  };
}

export function ThemeToggle() {
  const t = useTranslations("theme");
  // No servidor o tema é desconhecido (null); o cliente lê o valor real após hidratar.
  const theme = useSyncExternalStore<ThemeName | null>(subscribe, current, () => null);

  const next: ThemeName = theme === "dark" ? "light" : "dark";
  const toggle = () => {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // armazenamento indisponível: o tema vale só nesta visita
    }
  };
  const label = next === "dark" ? t("toDark") : t("toLight");

  return (
    <button type="button" className="theme-toggle" onClick={toggle} aria-label={label} title={label}>
      {theme === "dark" ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" />
        </svg>
      )}
    </button>
  );
}
