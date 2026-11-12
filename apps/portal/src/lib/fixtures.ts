// Dados de teste (forma do contrato /navigation). Só para testes automatizados.
import type { Kpi, Navigation } from "./types";

const kpi = (over: Partial<Kpi> & Pick<Kpi, "kpi_id" | "label">): Kpi =>
  ({
    theme_id: "pop",
    subtheme_id: "tamanho",
    indicator_id: over.kpi_id,
    name: over.label,
    description: "",
    unit: "Pessoas",
    additivity: "additive",
    periods: ["2022"],
    levels: ["brasil", "uf"],
    map_levels: ["uf"],
    dimensions: [],
    caveats: [],
    time_grains: [],
    source: { dataset_id: "d", source_table_id: "0", source_variable_id: "93", source_variable_name: null, reference_url: null, license_id: null },
    ...over,
  }) as Kpi;

const dim = (classification_id: string, label: string) =>
  ({ classification_id, label, partition_id: "p", total_category_key: "t", categories: [] }) as unknown as Kpi["dimensions"][number];

export const navFixture: Navigation = {
  release_id: "81f68da1-6c5f-4686-9ea9-6818a24b8db4",
  scope: "beta",
  dimension_order: ["c86", "c2"],
  themes: [
    {
      theme_id: "pop",
      label: "População e demografia",
      filters: [],
      subthemes: [
        {
          subtheme_id: "tamanho",
          label: "Tamanho e crescimento",
          kpis: [
            kpi({
              kpi_id: "populacao_estimada",
              label: "População estimada",
              description: "Estimativa anual oficial da população residente, publicada para o cálculo de cotas do Fundo de Participação dos Estados e Municípios.",
              periods: ["2001", "2002", "2026"],
              caveats: ["Limitação de teste."],
              source: { dataset_id: "d", source_table_id: "6579", source_variable_id: "9324", source_variable_name: null, reference_url: "https://sidra.ibge.gov.br/tabela/6579", license_id: "ibge-reuso-com-citacao" },
            }),
            kpi({
              kpi_id: "populacao_residente",
              label: "População residente (Censo)",
              dimensions: [dim("c86", "Cor ou raça"), dim("c2", "Sexo")],
              source: { dataset_id: "d", source_table_id: "9606", source_variable_id: "93", source_variable_name: null, reference_url: null, license_id: null },
            }),
          ],
          // Panorama (ADR-0010): item ainda sem dados, com a tabela prevista (dado de teste).
          planned: [
            { kpi_id: "item_em_preparacao", label: "Indicador de teste em preparação", source_table_id: "9999", survey: "Pesquisa de teste", filters: [], note: null },
          ],
        },
      ],
    },
    {
      theme_id: "saude",
      label: "Saúde",
      filters: [],
      subthemes: [
        {
          subtheme_id: "s",
          label: "",
          kpis: [kpi({ kpi_id: "doenca_cronica", label: "Pessoas com pelo menos uma doença crônica", theme_id: "saude", subtheme_id: "s", source: { dataset_id: "d", source_table_id: "7972", source_variable_id: "1", source_variable_name: null, reference_url: null, license_id: null } })],
          planned: [],
        },
      ],
    },
  ],
} as Navigation;
