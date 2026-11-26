import { HomeExplorer } from "@/components/HomeExplorer";
import { api } from "@/lib/api";
import { groupInstitutions } from "@/lib/sources";

export const dynamic = "force-dynamic";

// Início (Design System ODBr v2.3): busca, etiquetas de tema, grade de temas e prévia do indicador.
export default async function Home() {
  const [nav, sources, datasets] = await Promise.all([api.navigation(), api.sources(), api.datasets()]);
  // Nomes completos: "MS" (Ministério da Saúde) se confundiria com Mato Grosso do Sul.
  const institutions = groupInstitutions(sources, datasets).map((i) => i.name);
  return (
    <main className="page page-wide">
      <HomeExplorer nav={nav} institutions={institutions} />
    </main>
  );
}
