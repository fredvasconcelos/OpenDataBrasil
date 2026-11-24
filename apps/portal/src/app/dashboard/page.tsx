import { permanentRedirect } from "next/navigation";

/** Preserva filtros e parâmetros repetidos dos links antigos do Painel. */
export default async function DashboardRedirect({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(await searchParams)) {
    for (const item of Array.isArray(value) ? value : value === undefined ? [] : [value]) query.append(key, item);
  }
  permanentRedirect(`/estatisticas/painel${query.size ? `?${query}` : ""}`);
}
