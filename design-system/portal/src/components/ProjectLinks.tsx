"use client";

import { useTranslations } from "next-intl";

import { GithubIcon, MailIcon } from "@/components/icons";
import { CONTACT_URL, isExternal, REPO_URL } from "@/lib/links";

interface Props {
  variant: "header" | "footer";
  contactUrl?: string | null;
  repoUrl?: string | null;
}

// Contato + GitHub (Design System ODBr, seção 8).
// Cabeçalho: botão-pílula "Contato" e botão redondo só com o ícone do GitHub (rótulo em aria-label).
// Rodapé: dois links com ícone e texto ("Contato", "Código no GitHub").
export function ProjectLinks({ variant, contactUrl = CONTACT_URL, repoUrl = REPO_URL }: Props) {
  const t = useTranslations("nav");
  const ext = (href: string) => (isExternal(href) ? { target: "_blank", rel: "noopener noreferrer" } : {});
  if (variant === "header") {
    return (
      <>
        {contactUrl ? (
          <a className="header-contact" href={contactUrl} {...ext(contactUrl)}>
            <MailIcon />
            {t("contact")}
          </a>
        ) : null}
        {repoUrl ? (
          <a className="icon-btn" href={repoUrl} aria-label={t("repo")} title={t("repo")} {...ext(repoUrl)}>
            <GithubIcon />
          </a>
        ) : null}
      </>
    );
  }
  return (
    <>
      {contactUrl ? (
        <a href={contactUrl} {...ext(contactUrl)}>
          <MailIcon />
          {t("contact")}
        </a>
      ) : null}
      {repoUrl ? (
        <a href={repoUrl} {...ext(repoUrl)}>
          <GithubIcon size={16} />
          {t("code")}
        </a>
      ) : null}
    </>
  );
}
