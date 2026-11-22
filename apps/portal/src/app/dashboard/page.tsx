import { Suspense } from "react";

import { Dashboard } from "@/components/Dashboard";
import { api, ApiRequestError } from "@/lib/api";
import { resolveKpiId } from "@/lib/state";

export const dynamic = "force-dynamic";

export default async function DashboardPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const requested = typeof params.kpi === "string" ? params.kpi : null;
  const [index, snapshot] = await Promise.all([
    api.index(),
    requested && /^[a-z][a-z0-9_]{0,63}$/.test(requested) ? api.kpiSnapshot(requested).catch((error: unknown) => {
      if (error instanceof ApiRequestError && error.status === 404) return null;
      throw error;
    }) : null,
  ]);
  const id = resolveKpiId(new URLSearchParams(requested ? { kpi: requested } : {}), index);
  const initialKpi = id ? snapshot?.kpi.kpi_id === id && snapshot.releaseId === index.release_id
    ? snapshot.kpi : await api.kpi(id, index.release_id) : null;
  return (
    <Suspense>
      <Dashboard index={index} initialKpi={initialKpi} />
    </Suspense>
  );
}
