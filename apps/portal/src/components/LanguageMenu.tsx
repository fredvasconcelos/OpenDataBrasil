"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { GlobeIcon } from "@/components/icons";
import { LOCALES } from "@/i18n/locales";

// Seletor de idioma (DS 2.9; só no cabeçalho e na gaveta desde o DS 2.10): globo + sigla ("PT"). Abre uma lista com os idiomas do
// portal; os que ainda não têm tradução aparecem desativados, com "em breve". Fecha com
// Esc (o foco volta ao botão), ao clicar fora e ao escolher.
export function LanguageMenu() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const current = LOCALES.find((l) => l.code === locale) ?? LOCALES[0]!;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    const onDown = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  return (
    <div className="lang" ref={box}>
      <button
        ref={button}
        type="button"
        className="lang-btn"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={t("languageCurrent", { language: current.name })}
        title={t("language")}
        onClick={() => setOpen((o) => !o)}
      >
        <GlobeIcon size={16} />
        <span aria-hidden="true">{current.short}</span>
        <span className="lang-caret" aria-hidden="true">
          ▾
        </span>
      </button>
      {open ? (
        <ul id={listId} className="lang-list" aria-label={t("language")}>
          {LOCALES.map((l) => (
            <li key={l.code}>
              <button
                type="button"
                lang={l.code}
                aria-current={l.code === current.code ? "true" : undefined}
                disabled={!l.ready}
                onClick={() => {
                  setOpen(false);
                  button.current?.focus();
                }}
              >
                <span className="lang-short" aria-hidden="true">
                  {l.short}
                </span>
                <span className="lang-name">{l.name}</span>
                {l.ready ? null : (
                  <span className="lang-soon" lang="pt-BR">
                    {t("languageSoon")}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
