"use client";

import { useTranslations } from "next-intl";

import { GithubIcon, InstagramIcon, MailIcon } from "@/components/icons";
import { CONTACT_URL, INSTAGRAM_URL, isExternal, REPO_URL } from "@/lib/links";

interface Props {
  variant: "header" | "footer" | "drawer";
  contactUrl?: string | null;
  instagramUrl?: string | null;
  repoUrl?: string | null;
}

/** Atributos de um link de contato ou rede: http(s) abre em nova aba; "mailto:" não. */
export const linkTarget = (href: string) => (isExternal(href) ? { target: "_blank", rel: "noopener noreferrer" } : {});

// Contato, Instagram e GitHub (DS 2.10). Cada link só aparece quando configurado (lib/links.ts).
// - header: Instagram e GitHub, botões redondos só com ícone (rótulo em aria-label e title).
//   O Contato fica no menu principal, em texto, ao lado de "Sobre os dados" (Header);
// - drawer (gaveta mobile): Instagram e GitHub em pílulas com ícone e texto (o Contato vai
//   na lista de páginas);
// - footer: Contato (e-mail), Instagram e GitHub, os três como ícones redondos.
export function ProjectLinks({
  variant,
  contactUrl = CONTACT_URL,
  instagramUrl = INSTAGRAM_URL,
  repoUrl = REPO_URL,
}: Props) {
  const t = useTranslations("nav");
  const all = [
    { id: "contact", href: contactUrl, icon: <MailIcon size={16} />, label: t("contact"), text: t("contact") },
    { id: "instagram", href: instagramUrl, icon: <InstagramIcon size={17} />, label: t("instagram"), text: t("instagramShort") },
    { id: "repo", href: repoUrl, icon: <GithubIcon size={17} />, label: t("repo"), text: t("code") },
  ].filter((l): l is typeof l & { href: string } => Boolean(l.href));
  const links = variant === "footer" ? all : all.filter((l) => l.id !== "contact");

  if (variant === "drawer") {
    return (
      <>
        {links.map((l) => (
          <a key={l.id} href={l.href} {...linkTarget(l.href)}>
            {l.icon}
            {l.text}
          </a>
        ))}
      </>
    );
  }
  const className = variant === "header" ? "icon-btn" : "footer-icon";
  return (
    <>
      {links.map((l) => (
        <a key={l.id} className={className} href={l.href} aria-label={l.label} title={l.label} {...linkTarget(l.href)}>
          {l.icon}
        </a>
      ))}
    </>
  );
}
