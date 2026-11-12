"""Modelos de resposta e de requisição (OpenAPI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GEOGRAPHY_KEY = r"^[a-z_]{2,32}:[0-9A-Za-z]{1,16}$"
ID = r"^[a-z][a-z0-9_]{0,63}$"


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class TableVersionOut(_Out):
    """Tabela Gold e versão Delta usadas na resposta."""

    table_id: str
    delta_version: int


class Provenance(_Out):
    """De onde veio o resultado."""

    release_id: str
    tables: list[TableVersionOut]
    derived: bool = False
    truncated: bool = False


class ErrorBody(_Out):
    """Corpo de erro padronizado."""

    code: str
    message: str


class ErrorOut(_Out):
    """Resposta de erro."""

    error: ErrorBody


class SourceOut(_Out):
    """Fonte de dados."""

    source_id: str
    institution_id: str
    name: str
    connector_type: str
    base_url: str
    documentation_url: str | None


class LicenseOut(_Out):
    """Licença de reutilização."""

    license_id: str
    name: str
    url: str | None
    conditions: str
    review_status: str


class DatasetOut(_Out):
    """Dataset do catálogo."""

    dataset_id: str
    source_id: str
    official_id: str
    title: str
    description: str
    periodicity: str
    reference_url: str | None
    access_classification: str
    license: LicenseOut


class ReleaseOut(_Out):
    """Release ativo."""

    release_id: str
    scope: str
    activated_at: str | None
    code_version: str
    tables: list[TableVersionOut]


class IndicatorOut(_Out):
    """Indicador publicado no release."""

    indicator_id: str
    name: str
    description: str
    unit: str
    additivity: str
    concept: str
    theme_path: list[str]
    dataset_id: str
    source_table_id: str
    source_variable_id: str
    source_variable_name: str | None
    classification_ids: list[str]
    available_levels: list[str]
    periods: list[str]
    caveats: list[str]
    reference_url: str | None
    license_id: str | None


class TreeNodeOut(_Out):
    """Nó da árvore temática da Gold."""

    node_key: str
    parent_key: str | None
    node_type: str
    label: str
    depth: int
    indicator_id: str | None
    classification_id: str | None
    category_key: str | None


class GeographyOut(_Out):
    """Território."""

    geography_key: str
    level_id: str
    level_name: str | None
    territory_code: str
    name: str
    uf_abbreviation: str | None
    parent_key: str | None


class CategoryOut(_Out):
    """Categoria de uma dimensão exposta."""

    category_key: str
    category_id: str
    name: str


class DimensionOut(_Out):
    """Dimensão exposta de um KPI."""

    classification_id: str
    label: str
    partition_id: str
    total_category_key: str
    categories: list[CategoryOut]


class KpiSourceOut(_Out):
    """Fonte oficial do KPI."""

    dataset_id: str
    source_table_id: str
    source_variable_id: str
    source_variable_name: str | None
    reference_url: str | None
    license_id: str | None
    # Quem publica e por qual sistema (ex.: "IBGE" e "SIDRA"; "MJSP" e None para o Sinesp).
    institution: str | None = None
    system: str | None = None


Grain = Literal["mes", "trimestre", "semestre", "ano"]


class TimeGrainOut(_Out):
    """Grão de tempo de um KPI (ADR-0013): o publicado e os somados a partir dele."""

    grain: str
    label: str
    periods: list[str]
    # Períodos com todas as partes publicadas (ex.: o ano com os 12 meses).
    complete_periods: list[str]


class KpiOut(_Out):
    """KPI do portal com os metadados do indicador no release."""

    kpi_id: str
    label: str
    theme_id: str
    subtheme_id: str
    indicator_id: str
    name: str
    description: str
    unit: str
    additivity: str
    periods: list[str]
    levels: list[str]
    map_levels: list[str]
    dimensions: list[DimensionOut]
    caveats: list[str]
    # O primeiro é o grão publicado; os demais são somas (só fluxos). Vazio sem períodos.
    time_grains: list[TimeGrainOut] = []
    source: KpiSourceOut


class FilterOut(_Out):
    """Filtro previsto para um tema do panorama (ex.: sexo, produto)."""

    filter_id: str
    label: str


class PlannedKpiOut(_Out):
    """KPI do panorama ainda sem dados publicados ("em preparação")."""

    kpi_id: str
    label: str
    source_table_id: str = Field(description="Código da tabela no SIDRA.")
    survey: str = Field(description="Pesquisa de origem (inferida do acervo).")
    filters: list[str] = Field(description="Filtros previstos (filter_id).")
    note: str | None


class SubthemeOut(_Out):
    """Subtema da navegação."""

    subtheme_id: str
    label: str
    kpis: list[KpiOut]
    planned: list[PlannedKpiOut] = Field(description="KPIs do panorama em preparação.")


class ThemeOut(_Out):
    """Tema da navegação."""

    theme_id: str
    label: str
    filters: list[FilterOut] = Field(description="Filtros previstos para o tema.")
    subthemes: list[SubthemeOut]


class NavigationOut(_Out):
    """Navegação do portal no release ativo."""

    release_id: str
    scope: str
    dimension_order: list[str]
    themes: list[ThemeOut]


class MapValueOut(_Out):
    """Valor de um território no mapa."""

    geography_key: str
    name: str
    value: float | None
    status: str


class MapOut(_Out):
    """Valores do KPI por território (Total), para colorir o mapa."""

    kpi_id: str
    indicator_id: str
    level: str
    period: str
    # Grão somado a partir do publicado (ADR-0013); None: valores publicados.
    grain: str | None = None
    unit: str
    additivity: str
    # "total": o valor do KPI; "share": a participação de uma categoria no Total (%).
    measure: Literal["total", "share"] = "total"
    measure_label: str | None = None
    values: list[MapValueOut]
    provenance: Provenance


class GeographyRefOut(_Out):
    """Referência curta a um território."""

    geography_key: str
    name: str
    level_id: str


class DetailNodeOut(_Out):
    """Nó do tooltip: categoria, valor e participação no nó de cima."""

    label: str
    classification_id: str | None
    category_key: str | None
    value: float | None
    status: str
    share_pct: float | None
    children: list[DetailNodeOut] = Field(default_factory=list)


class DetailOut(_Out):
    """Detalhe de um território (tooltip): sub-KPIs aninhados."""

    kpi_id: str
    indicator_id: str
    geography: GeographyRefOut
    period: str
    # Grão somado a partir do publicado (ADR-0013); None: valores publicados.
    grain: str | None = None
    unit: str
    additivity: str
    dimensions: list[str]
    root: DetailNodeOut
    notes: list[str]
    provenance: Provenance


class PointOut(_Out):
    """Ponto de uma série."""

    period: str
    value: float | None
    status: str


class SeriesItemOut(_Out):
    """Série de uma combinação de categorias."""

    key: str
    label: str
    categories: dict[str, str]
    points: list[PointOut]


class SeriesOut(_Out):
    """Evolução temporal de um território."""

    kpi_id: str
    indicator_id: str
    geography: GeographyRefOut
    unit: str
    grain: str | None = None
    series: list[SeriesItemOut]
    provenance: Provenance


class ColumnOut(_Out):
    """Coluna da tabela (uma combinação de categorias)."""

    key: str
    label: str
    depth: int


class CellOut(_Out):
    """Célula da tabela."""

    value: float | None
    status: str


class TableRowOut(_Out):
    """Linha da tabela (um território)."""

    geography_key: str
    name: str
    uf_abbreviation: str | None
    cells: dict[str, CellOut]


class TableOut(_Out):
    """Tabela paginada de territórios."""

    kpi_id: str
    indicator_id: str
    level: str
    period: str
    # Grão somado a partir do publicado (ADR-0013); None: valores publicados.
    grain: str | None = None
    unit: str
    columns: list[ColumnOut]
    rows: list[TableRowOut]
    total_rows: int
    offset: int
    limit: int
    provenance: Provenance


class QueryIn(BaseModel):
    """Consulta estruturada sobre indicadores (sem SQL)."""

    model_config = ConfigDict(extra="forbid")

    indicators: list[str] = Field(min_length=1, max_length=10)
    level: str = Field(pattern=ID)
    within: str | None = Field(default=None, pattern=GEOGRAPHY_KEY)
    periods: list[str] = Field(default_factory=list, max_length=50)
    breakdown: dict[str, list[str] | None] = Field(default_factory=dict, max_length=6)
    sum_to: str | None = Field(default=None, pattern=ID)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=1000, ge=1)


class QueryRowOut(_Out):
    """Linha do resultado de ``/query``."""

    indicator_id: str
    geography_key: str
    territory_name: str
    level_id: str
    period: str
    breakdown_key: str
    breakdown_label: str
    value: float | None
    value_status: str
    unit: str


class QueryOut(_Out):
    """Resultado de ``/query``."""

    rows: list[QueryRowOut]
    # Há linhas depois desta página (a contagem total não é calculada).
    has_more: bool
    offset: int
    limit: int
    warnings: list[str]
    provenance: Provenance


ExportFormat = Literal["csv", "xlsx", "parquet", "json"]


class ExportIn(BaseModel):
    """Exportação de um KPI."""

    model_config = ConfigDict(extra="forbid")

    kpi_id: str = Field(pattern=ID)
    level: str = Field(pattern=ID)
    within: str | None = Field(default=None, pattern=GEOGRAPHY_KEY)
    periods: list[str] = Field(default_factory=list, max_length=50)
    dimensions: list[str] = Field(default_factory=list, max_length=6)
    grain: Grain | None = None
    format: ExportFormat = "csv"
