import { useTranslations } from "next-intl";

import type { InstitutionSources } from "@/lib/sources";

// "De onde vêm os dados" (página Sobre): instituições e fontes montadas a partir do catálogo
// (lib/sources.ts), nunca escritas à mão. Cada fonte leva à documentação oficial.
export function SourceList({ institutions }: { institutions: InstitutionSources[] }) {
  const t = useTranslations("about");
  if (!institutions.length) return null;
  return (
    <section className="source-list" id="fontes" aria-labelledby="fontes-titulo">
      <h2 id="fontes-titulo">{t("sourcesTitle")}</h2>
      <p className="support-note">{t("sourcesLead")}</p>
      <ul>
        {institutions.map((inst) => (
          <li key={inst.id} className="source-card">
            <h3>
              {inst.url ? (
                <a href={inst.url} target="_blank" rel="noopener noreferrer">
                  {inst.name}
                  <span className="sr-only"> {t("newTab")}</span>
                </a>
              ) : (
                inst.name
              )}
              {inst.acronym ? <span className="source-acronym">{inst.acronym}</span> : null}
            </h3>
            <ul>
              {inst.sources.map((s) => (
                <li key={s.id}>
                  <a href={s.url} target="_blank" rel="noopener noreferrer">
                    {s.name}
                    <span className="sr-only"> {t("newTab")}</span>
                  </a>
                  <span className="muted small">{t("sourceDatasets", { count: s.datasets })}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
