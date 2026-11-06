"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

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
      <header className="header">
        <Link href="/" className="brand">
          {t("site.name")}
        </Link>
        <nav aria-label="Principal">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={path === l.href ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
      </header>
      <p className="notice" role="note">
        {t("site.internalNotice")}
      </p>
    </>
  );
}
