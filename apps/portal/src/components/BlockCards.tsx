import Link from "next/link";
import { useTranslations } from "next-intl";

import { BLOCKS } from "@/lib/blocks";
import { FaIcon } from "@/components/FaIcon";

// Início: as duas portas do portal (ADR-0039). Ícone, nome, descrição curta e entrada.
// Lado a lado a partir de 992 px; empilhadas abaixo.
export function BlockCards() {
  const t = useTranslations("blocks");
  return (
    <section className="block-cards" aria-labelledby="blocos-titulo">
      <h2 id="blocos-titulo" className="block-cards-title">{t("title")}</h2>
      <ul>
        {BLOCKS.map((b) => (
          <li key={b.id} className="block-card" data-block={b.id}>
            <span className="block-card-icon" aria-hidden="true">
              <FaIcon icon={b.icon} size={30} />
            </span>
            <h3>{t(`${b.id}.name`)}</h3>
            <p>{t(`${b.id}.description`)}</p>
            <Link href={b.href} className="block-card-link">
              {t("open")}
              <span className="sr-only">: {t(`${b.id}.name`)}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
