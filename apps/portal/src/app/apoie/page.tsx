import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { BugIcon, CodeIcon, DatabaseIcon, ShareIcon } from "@/components/icons";
import { SupportOptions } from "@/components/SupportOptions";
import { CONTACT_URL, isExternal, REPO_URL } from "@/lib/links";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("support");
  return { title: t("metaTitle"), description: t("lead") };
}

const SPENDING = ["server", "domain", "backup", "growth"] as const;

// Apoie o projeto (referência: f-droid.org/pt/contribute): por que doar, formas de doação,
// para onde vai o dinheiro (só categorias, sem estimativas) e outras formas de ajudar.
export default async function Support() {
  const t = await getTranslations("support");
  const ext = (href: string) => (isExternal(href) ? { target: "_blank", rel: "noopener noreferrer" } : {});
  const help = [
    { id: "share", icon: <ShareIcon />, href: null },
    { id: "report", icon: <BugIcon />, href: CONTACT_URL },
    { id: "suggest", icon: <DatabaseIcon />, href: CONTACT_URL },
    { id: "code", icon: <CodeIcon />, href: REPO_URL },
  ];
  return (
    <main className="page page-wide support-page">
      <section className="page-intro">
        <p className="eyebrow">{t("eyebrow")}</p>
        <h1>{t("title")}</h1>
        <p className="lead">{t("lead")}</p>
      </section>

      <section className="support-why" aria-labelledby="apoie-por-que">
        <h2 id="apoie-por-que">{t("why.title")}</h2>
        <ul>
          {(["free", "independent", "open"] as const).map((k) => (
            <li key={k}>
              <strong>{t(`why.${k}.title`)}</strong> {t(`why.${k}.text`)}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="apoie-doar">
        <h2 id="apoie-doar">{t("donate.title")}</h2>
        <SupportOptions />
      </section>

      <section aria-labelledby="apoie-gastos">
        <h2 id="apoie-gastos">{t("spending.title")}</h2>
        <p className="support-note">{t("spending.lead")}</p>
        <ul className="support-list">
          {SPENDING.map((k) => (
            <li key={k}>
              <strong>{t(`spending.${k}.title`)}</strong>
              <span>{t(`spending.${k}.text`)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="apoie-ajudar">
        <h2 id="apoie-ajudar">{t("help.title")}</h2>
        <ul className="support-grid support-grid-help">
          {help.map((h) => (
            <li key={h.id} className="support-card support-card-plain">
              <span className="support-card-icon">{h.icon}</span>
              <h3>{t(`help.${h.id}.title`)}</h3>
              <p>{t(`help.${h.id}.text`)}</p>
              {h.href ? (
                <a className="support-link" href={h.href} {...ext(h.href)}>
                  {t(`help.${h.id}.action`)}
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
