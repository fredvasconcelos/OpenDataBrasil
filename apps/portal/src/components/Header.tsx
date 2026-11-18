"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { CloseIcon, HeartIcon, MenuIcon } from "@/components/icons";
import { LanguageMenu } from "@/components/LanguageMenu";
import { Logo } from "@/components/Logo";
import { linkTarget, ProjectLinks } from "@/components/ProjectLinks";
import { ThemeToggle } from "@/components/ThemeToggle";
import { CONTACT_URL } from "@/lib/links";

// Cabeçalho (DS 2.10, opção 4; DS 2.12: Métricas). Menu: Início · Painel de análise · Sobre
// os dados · Contato (texto, mesmo estilo das abas) · Métricas e, logo depois, "Apoie" em amarelo da marca. À direita,
// dois blocos de 36 px: redes (Instagram e GitHub, só ícones) | preferências (idioma e
// tema). Até 899 px: logo, "Apoie" (só o coração) e o botão de menu, que abre uma gaveta
// com as páginas (Contato e Apoie inclusos), as redes, o idioma e o tema. A gaveta fecha
// ao trocar de página, com Esc e ao tocar fora; o foco volta para o botão de menu.
export function Header() {
  const notice = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    const node = notice.current;
    if (!node) return;
    const measure = () => document.documentElement.style.setProperty("--notice-h", `${node.getBoundingClientRect().height}px`);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => { observer.disconnect(); document.documentElement.style.removeProperty("--notice-h"); };
  }, []);
  const t = useTranslations();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const links = [
    { href: "/", label: t("nav.home") },
    { href: "/dashboard", label: t("nav.dashboard") },
    { href: "/sobre", label: t("nav.about") },
  ];

  // Fecha ao navegar (ajuste de estado durante a renderização, sem efeito em cascata).
  const [seenPath, setSeenPath] = useState(path);
  if (seenPath !== path) {
    setSeenPath(path);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <a className="skip" href="#conteudo">
        {t("nav.skip")}
      </a>
      <div className="brand-stripe" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <header className="header">
        <Link href="/" className="brand" aria-label={t("site.name")}>
          <Logo label={t("site.name")} />
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-name" aria-hidden="true">
            {t("site.name")}
          </span>
        </Link>
        <nav aria-label="Principal" className="header-nav">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={path === l.href ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
          {CONTACT_URL ? (
            <a href={CONTACT_URL} {...linkTarget(CONTACT_URL)}>
              {t("nav.contact")}
            </a>
          ) : null}
          <Link href="/metricas" aria-current={path === "/metricas" ? "page" : undefined}>
            {t("nav.metrics")}
          </Link>
        </nav>
        <Link
          href="/apoie"
          className="header-support"
          aria-label={t("nav.supportLong")}
          aria-current={path === "/apoie" ? "page" : undefined}
        >
          <HeartIcon size={16} />
          <span aria-hidden="true">{t("nav.support")}</span>
        </Link>
        <div className="header-end">
          <div className="header-desktop">
            <div className="header-group" role="group" aria-label={t("nav.social")}>
              <ProjectLinks variant="header" />
            </div>
            <span className="header-sep" aria-hidden="true" />
            <div className="header-group" role="group" aria-label={t("nav.preferences")}>
              <LanguageMenu />
              <ThemeToggle />
            </div>
          </div>
          <button
            ref={button}
            type="button"
            className="icon-btn menu-btn"
            aria-expanded={open}
            aria-controls="menu-movel"
            aria-label={open ? t("nav.closeMenu") : t("nav.openMenu")}
            onClick={() => setOpen((o) => !o)}
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </header>
      {open ? (
        <>
          <button type="button" className="drawer-backdrop" aria-label={t("nav.closeMenu")} tabIndex={-1} onClick={() => setOpen(false)} />
          <div id="menu-movel" className="drawer" role="dialog" aria-modal="false" aria-label={t("nav.menu")}>
            <nav aria-label={t("nav.menu")}>
              {links.map((l) => (
                <Link key={l.href} href={l.href} aria-current={path === l.href ? "page" : undefined}>
                  {l.label}
                </Link>
              ))}
              {CONTACT_URL ? (
                <a href={CONTACT_URL} {...linkTarget(CONTACT_URL)}>
                  {t("nav.contact")}
                </a>
              ) : null}
              <Link href="/metricas" aria-current={path === "/metricas" ? "page" : undefined}>
                {t("nav.metrics")}
              </Link>
              <Link href="/apoie" aria-current={path === "/apoie" ? "page" : undefined}>
                {t("nav.supportLong")}
              </Link>
            </nav>
            <div className="drawer-links">
              <ProjectLinks variant="drawer" />
            </div>
            <div className="drawer-theme">
              <span>{t("nav.language")}</span>
              <LanguageMenu />
            </div>
            <div className="drawer-theme">
              <span>{t("nav.theme")}</span>
              <ThemeToggle />
            </div>
          </div>
        </>
      ) : null}
      <p ref={notice} className="notice" role="note">
        {t("site.internalNotice")}
      </p>
    </>
  );
}
