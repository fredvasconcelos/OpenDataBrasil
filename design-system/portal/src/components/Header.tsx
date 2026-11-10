"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";

export function Header() {
  const t = useTranslations();
  const path = usePathname();
  const links = [
    { href: "/", label: t("nav.home") },
    { href: "/dashboard", label: t("nav.dashboard") },
    { href: "/sobre", label: t("nav.about") },
  ];
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
        <nav aria-label="Principal">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={path === l.href ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="header-end">
          <ThemeToggle />
        </div>
      </header>
      <p className="notice" role="note">
        {t("site.internalNotice")}
      </p>
    </>
  );
}
