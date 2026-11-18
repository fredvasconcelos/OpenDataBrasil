import { getTranslations } from "next-intl/server";

import { AboutCatalog } from "@/components/AboutCatalog";
import { SourceList } from "@/components/SourceList";
import { api } from "@/lib/api";
import { groupInstitutions } from "@/lib/sources";

export const dynamic = "force-dynamic";

// Sobre os dados (Design System ODBr v2.4.2): instituições e fontes, release ativo, números e catálogo por tema com
// todos os metadados de cada indicador. A situação da licença vem de /datasets.
export default async function About() {
  const t = await getTranslations("about");
  const [nav, release, datasets, sources] = await Promise.all([
    api.navigation(),
    api.release(),
    api.datasets(),
    api.sources(),
  ]);
  const activated = release.activated_at
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(
        new Date(release.activated_at),
      )
    : null;
  // Situação das licenças em uma frase: basta uma em revisão para o selo dizer "algumas em revisão".
  const statuses = new Set(datasets.map((d) => d.license.review_status));
  const reviews = statuses.has("requires_review") ? [t("reviewStatus.requires_review")] : statuses.size ? [t("reviewStatus.approved")] : [];
  return (
    <main className="page page-wide">
      <section className="page-intro">
        <h1>{t("title")}</h1>
        <p className="lead">{t("lead")}</p>
      </section>
      <SourceList institutions={groupInstitutions(sources, datasets)} />
      <AboutCatalog nav={nav} releaseId={release.release_id} activated={activated} licenseReview={reviews.length ? reviews.join(", ") : null} />
    </main>
  );
}
