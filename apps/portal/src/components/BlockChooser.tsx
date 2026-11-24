"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { FaIcon } from "@/components/FaIcon";
import { BLOCKS, blockOf, type BlockId } from "@/lib/blocks";

// "Painel de análise" abre a escolha do bloco (ADR-0039, seção 3). É o único lugar para
// trocar de bloco. Desktop: popover ancorado no botão; Esc e clique fora fecham e o foco
// volta ao botão. Na gaveta do celular, as duas opções aparecem em lista (variant="drawer").
function Options({ current, onPick }: { current: BlockId | null; onPick?: () => void }) {
  const t = useTranslations("blocks");
  return (
    <ul className="block-options">
      {BLOCKS.map((b) => (
        <li key={b.id}>
          <Link href={b.href} className="block-option" data-block={b.id} aria-current={current === b.id ? "page" : undefined} onClick={onPick}>
            <span className="block-option-icon" aria-hidden="true">
              <FaIcon icon={b.icon} size={18} />
            </span>
            <span className="block-option-text">
              <span className="block-option-name">{t(`${b.id}.name`)}</span>
              <span className="block-option-short">{t(`${b.id}.short`)}</span>
            </span>
            {current === b.id ? <span className="block-option-here">{t("current")}</span> : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function BlockChooser({ variant = "header", defaultOpen = false }: { variant?: "header" | "drawer"; defaultOpen?: boolean }) {
  const t = useTranslations();
  const path = usePathname();
  const current = blockOf(path);
  const [open, setOpen] = useState(defaultOpen);
  const button = useRef<HTMLButtonElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open || variant !== "header") return;
    box.current?.querySelector<HTMLAnchorElement>("a")?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (!box.current?.contains(target) && !button.current?.contains(target)) {
        setOpen(false);
        button.current?.focus({ preventScroll: true });
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, variant]);

  if (variant === "drawer") {
    return (
      <div className="block-drawer" role="group" aria-label={t("nav.dashboard")}>
        <span className="block-drawer-title">{t("nav.dashboard")}</span>
        <Options current={current} />
      </div>
    );
  }

  return (
    <div className="block-chooser">
      <button
        ref={button}
        type="button"
        className="block-chooser-btn"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-current={current ? "page" : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        {t("nav.dashboard")}
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ transform: open ? "rotate(180deg)" : "none" }}>
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open ? (
        <div ref={box} id={id} className="block-popover" role="dialog" aria-label={t("nav.chooseBlock")}>
          <p className="block-popover-title">{t("nav.chooseBlock")}</p>
          <Options current={current} onPick={() => setOpen(false)} />
        </div>
      ) : null}
    </div>
  );
}
