"use client";

import { useTranslations } from "next-intl";

import { formatCount, SUPPRESSION_THRESHOLD, type ValueLabels } from "@/lib/metrics";

/** Rótulos de "sem acessos" e "menos de 5" para viewsText (página Métricas). */
export function useValueLabels(): ValueLabels {
  const t = useTranslations("metrics");
  return { noAccess: t("noAccess"), lessThan: t("lessThan", { n: formatCount(SUPPRESSION_THRESHOLD) }) };
}
