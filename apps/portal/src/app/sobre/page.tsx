import { getTranslations } from "next-intl/server";

import { AboutCatalog } from "@/components/AboutCatalog";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

// Sobre os dados (Design System ODBr v2.3): release ativo, números e catálogo por tema com
// todos os metadados de cada indicador. A situação da licença vem de /datasets.
export default async function About() {
  const t = await getTranslations("about");
  const [nav, release, datasets] = await Promise.all([api.navigation(), api.release(), api.datasets()]);
  const activated = release.activated_at
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(
        new Date(release.activated_at),
      )
    : null;
  const reviews = [...new Set(datasets.map((d) => d.license.review_status).filter(Boolean))];
  return (
    <main className="page page-wide">
      <section className="page-intro">
        <h1>{t("title")}</h1>
        <p className="lead">{t("lead")}</p>
      </section>
      <AboutCatalog nav={nav} releaseId={release.release_id} activated={activated} licenseReview={reviews.length ? reviews.join(", ") : null} />
    </main>
  );
}
