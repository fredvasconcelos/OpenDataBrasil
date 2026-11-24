import { Suspense } from "react";

import { ContasDashboard } from "@/components/contas/ContasDashboard";

export default function ContasPage() {
  return <Suspense><ContasDashboard /></Suspense>;
}
