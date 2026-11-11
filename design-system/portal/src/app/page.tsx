import { HomeCatalog } from "@/components/HomeCatalog";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

// Início (Design System ODBr v2.3): busca, etiquetas de tema, grade de temas e prévia do indicador.
export default async function Home() {
  const nav = await api.navigation();
  return (
    <main className="page page-wide">
      <HomeCatalog nav={nav} releaseId={nav.release_id ?? null} />
    </main>
  );
}
