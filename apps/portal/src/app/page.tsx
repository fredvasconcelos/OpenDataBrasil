import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { IndicatorSearch } from "@/components/IndicatorSearch";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const t = await getTranslations("home");
  const nav = await api.navigation();
  const kpis = nav.themes.flatMap((th) =>
    th.subthemes.flatMap((s) => s.kpis.map((k) => ({ ...k, path: `${th.label} › ${s.label}` }))),
  );
  return (
    <main className="page">
      <h1>{t("title")}</h1>
      <p className="muted">{t("lead")}</p>
      <IndicatorSearch kpis={kpis} />
      <h2>{t("themes")}</h2>
      {nav.themes.map((th) => (
        <section key={th.theme_id} className="card" style={{ marginBottom: 12 }}>
          <h3 style={{ marginTop: 0 }}>{th.label}</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
            {th.subthemes.map((s) => (
              <div key={s.subtheme_id}>
                <strong>{s.label}</strong>
                {s.kpis.length ? (
                  <ul className="small" style={{ paddingLeft: 18 }}>
                    {s.kpis.map((k) => (
                      <li key={k.kpi_id}>
                        <Link href={`/dashboard?kpi=${k.kpi_id}`}>{k.label}</Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {s.planned.length ? (
                  <p className="small home-planned">{t("plannedCount", { count: s.planned.length })}</p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
