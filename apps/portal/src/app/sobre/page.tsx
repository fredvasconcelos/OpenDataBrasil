import { getTranslations } from "next-intl/server";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function About() {
  const t = await getTranslations("about");
  const [release, datasets] = await Promise.all([api.release(), api.datasets()]);
  const activated = release.activated_at
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(
        new Date(release.activated_at),
      )
    : "–";
  return (
    <main className="page">
      <h1>{t("title")}</h1>
      <p>{t("lead")}</p>
      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("release")}</h2>
        <p>
          <code>{release.release_id}</code> · {t("activated", { date: activated })}
        </p>
      </section>
      <h2>{t("datasets")}</h2>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {datasets.map((d) => (
          <li key={d.dataset_id} className="card" style={{ marginBottom: 8 }}>
            <strong>{d.title}</strong> <span className="muted small">({d.official_id})</span>
            <p className="small" style={{ margin: "4px 0" }}>
              {d.description}
            </p>
            <p className="small muted" style={{ margin: 0 }}>
              {t("license")}: {d.license.name} · {t("review", { status: d.license.review_status })}
              {d.reference_url ? (
                <>
                  {" · "}
                  <a href={d.reference_url} target="_blank" rel="noreferrer">
                    {d.reference_url}
                  </a>
                </>
              ) : null}
            </p>
          </li>
        ))}
      </ul>
    </main>
  );
}
