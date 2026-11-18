import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { MetricsView } from "@/components/MetricsView";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metrics");
  return { title: t("title"), description: t("lead") };
}

// Métricas (DS 2.12, ADR-0027): acessos ao portal por País › Grande Região › Estado,
// ranking e indicadores mais acessados. Os dados vêm de /metrics/* no navegador; sem a
// coleta, a página diz que ela ainda não começou.
export default function Metrics() {
  return <MetricsView />;
}
