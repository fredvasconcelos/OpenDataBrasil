// Tipos derivados do contrato OpenAPI (src/lib/api-schema.ts, gerado por `npm run gen:api`).
import type { components } from "./api-schema";

type S = components["schemas"];
export type Navigation = S["NavigationOut"];
export type Theme = S["ThemeOut"];
export type Subtheme = S["SubthemeOut"];
export type Kpi = S["KpiOut"];
export type Dimension = S["DimensionOut"];
export type MapData = S["MapOut"];
export type MapValue = S["MapValueOut"];
export type Detail = S["DetailOut"];
export type DetailNode = S["DetailNodeOut"];
export type Series = S["SeriesOut"];
export type SeriesItem = S["SeriesItemOut"];
export type Table = S["TableOut"];
export type Release = S["ReleaseOut"];
export type Dataset = S["DatasetOut"];
export type Indicator = S["IndicatorOut"];
export type ExportFormat = S["ExportIn"]["format"];
export type ApiError = S["ErrorOut"];
export type Geography = S["GeographyOut"];

export interface GeoFeature {
  type: "Feature";
  id: string;
  properties: { name: string; uf: string | null };
  geometry: GeoJSON.Geometry;
}

export interface GeoCollection {
  type: "FeatureCollection";
  metadata: { release_id: string; level: string; within: string | null };
  features: GeoFeature[];
}
