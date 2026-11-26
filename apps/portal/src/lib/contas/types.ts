// Tipos do bloco Contas públicas, gerados do OpenAPI da API das contas (ADR-0037).
// Regenerar junto com o contrato completo: npm run gen:api.
import type { components } from "@/lib/api-schema";

type S = components["schemas"];

export type ContasMeta = S["ContasMetaOut"];
export type ContasMap = S["ContasMapOut"];
export type ContasComposition = S["ContasCompositionOut"];
export type ContasSeries = S["ContasSeriesOut"];
export type ContasRanking = S["ContasRankingOut"];
export type ContasTable = S["ContasTableOut"];
export type ContasProvenance = S["ContasProvenance"];
export type PeriodStatus = S["PeriodStatusOut"];
export type RecipientProfile = S["RecipientProfileOut"];
export type RecipientRef = S["RecipientRefOut"];
export type RankingRow = S["RankingRowOut"];
export type CompositionRow = S["CompositionRowOut"];

export type ContasExecution = S["ContasExecutionOut"];
export type ContasSearch = S["ContasSearchOut"];
export type ExecutionRow = S["ExecutionRowOut"];
export type ContasLens = "A" | "B" | "C";
