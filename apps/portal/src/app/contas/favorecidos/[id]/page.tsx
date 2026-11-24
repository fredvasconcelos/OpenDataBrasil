import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { ContasUnavailable } from "@/components/contas/ContasParts";
import { RecipientProfile } from "@/components/contas/RecipientProfile";
import { ApiRequestError } from "@/lib/api";
import { contasApi } from "@/lib/api/contas";
import { safePanelHref } from "@/lib/contas/state";

export const dynamic = "force-dynamic";
// A API não expõe identificadores; todas as fichas recebem a proteção exigida para PF.
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function RecipientPage({ params, searchParams }: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  if (!/^[0-9a-f]{16}$/.test(id)) notFound();
  const search = await searchParams;
  const backHref = safePanelHref(search.back);
  const requested = typeof search.year === "string" && /^20\d{2}$/.test(search.year) ? Number(search.year) : null;
  let profile;
  try {
    profile = await contasApi.recipient(id, requested ? [String(requested)] : undefined);
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) notFound();
    const t = await getTranslations("contas");
    return <main className="page"><Link href={backHref}>{t("profile.back")}</Link><ContasUnavailable /></main>;
  }
  const year = requested ?? profile.totals[profile.totals.length - 1]?.year;
  if (year === undefined) notFound();
  return <RecipientProfile profile={profile} year={year} backHref={backHref} />;
}
