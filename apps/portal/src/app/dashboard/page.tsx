import { Suspense } from "react";

import { Dashboard } from "@/components/Dashboard";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const nav = await api.navigation();
  return (
    <Suspense>
      <Dashboard nav={nav} />
    </Suspense>
  );
}
