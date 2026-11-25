import { useTranslations } from "next-intl";

import { CONTAS_REFERENCES } from "@/lib/contas/references";

/** Dicionários da CGU para interpretar os campos, separados da proveniência dos valores. */
export function ContasReferences({ recipient = false }: { recipient?: boolean }) {
  const t = useTranslations("contas.references");
  const current = recipient
    ? ["transfers", "receipts", "entities", "glossary"] as const
    : ["transfers", "receipts", "execution", "entities", "glossary"] as const;
  return (
    <details className="contas-references">
      <summary>{t("title")}</summary>
      <p>{t("lead")}</p>
      <ul>
        {current.map((key) => (
          <li key={key}>
            <a href={CONTAS_REFERENCES[key]} target="_blank" rel="noopener noreferrer">
              {t(key)}<span className="sr-only"> {t("newTab")}</span>
            </a>
          </li>
        ))}
      </ul>
      <p>{t(recipient ? "recipientNote" : "panelNote")}</p>
      <p>
        <a href={CONTAS_REFERENCES.history} target="_blank" rel="noopener noreferrer">
          {t("history")}<span className="sr-only"> {t("newTab")}</span>
        </a>
      </p>
      <p>{t("historyNote")}</p>
    </details>
  );
}
