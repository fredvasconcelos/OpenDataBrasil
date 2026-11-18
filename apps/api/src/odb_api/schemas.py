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
    # Correção por índice de preços aplicada (ADR-0020): id, rótulo e mês-base.
    correction: str | None = None
    correction_label: str | None = None
    price_base: str | None = None


class CorrectionOut(_Out):
    """Correção disponível para o KPI ("Corrigir por", ADR-0020)."""

    correction_id: str
    label: str
    note: str


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
    institution_name: str | None = None
    institution_acronym: str | None = None
    institution_url: str | None = None
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
    full_name: str = Field(
        "", description="Nome oficial completo (o rótulo pode ser o curto, DS 2.3.11)."
    )


class DimensionOut(_Out):
    """Dimensão exposta de um KPI."""

    classification_id: str
    label: str
    full_label: str = Field(
        "", description="Nome oficial completo (o rótulo pode ser o curto, DS 2.3.11)."
    )
    partition_id: str
    total_category_key: str
    categories: list[CategoryOut]
    # Níveis com o detalhe; vazio: todos os do KPI (ex.: situação na PNS, só Brasil).
    # Também restrito quando o release não traz as categorias num nível (DS 2.9).
    levels: list[str] = []
    # Tabelas de origem das categorias (tabelas-irmãs, ADR-0018), como no release.
    source_table_ids: list[str] = []


class SourceTableOut(_Out):
    """Tabela de origem de um KPI no release: o que ela traz e o link oficial."""

    table_id: str
    reference_url: str | None = None
    # Classificações com categorias vindas desta tabela (vazio: só o Total).
    classification_ids: list[str] = []
    periods: list[str] = []


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
    # Todas as tabelas de origem (a principal primeiro), com o que cada uma traz (DS 2.9).
    tables: list[SourceTableOut] = []


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
    # % das categorias sobre o Total (tabela, tooltip, série): somável ou quantidade.
    category_shares: bool = False
    periods: list[str]
    # Cobertura real: a POF tem municípios só em 2008; séries Censo + PNAD variam por nível.
    periods_by_level: dict[str, list[str]] = Field(default_factory=dict)
    levels: list[str]
    map_levels: list[str]
    dimensions: list[DimensionOut]
    # Dimensões marginais: detalhar uma por vez (ADR-0016).
    exclusive_dimensions: bool = False
    # Cruzamentos completos (C1): grupos de dimensões que se cruzam nesses níveis.
    crossed: list[list[str]] = []
    crossed_levels: list[str] = []
    # Correções por índice de preços (ADR-0020); vazio: só o valor nominal.
    corrections: list[CorrectionOut] = []
    caveats: list[str]
    # O primeiro é o grão publicado; os demais são somas (só fluxos). Vazio sem períodos.
    time_grains: list[TimeGrainOut] = []
    # Como os grãos maiores saem do publicado: "sum", "mean" ou "last" (ADR-0017).
    time_aggregation: Literal["sum", "mean", "last", "compound"] | None = None
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


class HealthOut(_Out):
    """Saúde do serviço (ADR-0015)."""

    status: Literal["ok"]
    release_id: str
    # "degraded": KPIs da configuração incoerentes com o release saíram da navegação.
    portal: Literal["ok", "degraded"]
    unavailable_kpis: dict[str, list[str]] = Field(
        description="KPI → problemas contra o release ativo (vazio quando o portal está ok)."
    )


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
    periods: list[str] = Field(
        default_factory=list,
        description="Períodos da consulta com vários períodos (ADR-0026); vazio: só ``period``.",
    )
    accumulated: str | None = Field(
        default=None, description="Acumulado: total, running (corrente) ou year (no ano)."
    )
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
    full_label: str = Field(
        "", description="Nome oficial completo (o rótulo pode ser o curto, DS 2.3.11)."
    )
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
    periods: list[str] = Field(
        default_factory=list,
        description="Períodos da consulta com vários períodos (ADR-0026); vazio: só ``period``.",
    )
    accumulated: str | None = Field(
        default=None, description="Acumulado: total, running (corrente) ou year (no ano)."
    )
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
    # Tabela de origem do ponto (séries compostas de fontes distintas, ADR-0022).
    source_table_id: str | None = None


class SeriesItemOut(_Out):
    """Série de uma combinação de categorias."""

    key: str
    label: str
    full_label: str = Field(
        "", description="Nome oficial completo (o rótulo pode ser o curto, DS 2.3.11)."
    )
    categories: dict[str, str]
    depth: int = Field(
        0,
        description=(
            "Quantas dimensões estão detalhadas nesta série: 0 é o Total; o maior valor são"
            " as combinações mais detalhadas."
        ),
    )
    points: list[PointOut]


class SeriesOut(_Out):
    """Evolução temporal de um território."""

    kpi_id: str
    indicator_id: str
    geography: GeographyRefOut
    unit: str
    grain: str | None = None
    accumulated: str | None = Field(
        default=None, description="Acumulado: running (corrente) ou year (no ano), ADR-0026."
    )
    series: list[SeriesItemOut]
    provenance: Provenance


class ColumnOut(_Out):
    """Coluna da tabela (uma combinação de categorias)."""

    key: str
    label: str
    full_label: str = Field(
        "", description="Nome oficial completo (o rótulo pode ser o curto, DS 2.3.11)."
    )
    depth: int
    # Matriz (DS 2.3.9): coluna-grupo (categoria da primeira dimensão, ou o Total) e a
    # combinação-mãe (a mesma com a última categoria detalhada trocada pelo Total).
    group: str = Field("total", description="Chave da coluna-grupo (primeira dimensão).")
    parent: str | None = Field(None, description="Chave da combinação-mãe (% no grupo).")
    period: str | None = Field(
        default=None, description="Período da coluna (tabela com vários períodos)."
    )


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
    periods: list[str] = Field(
        default_factory=list,
        description="Períodos da consulta com vários períodos (ADR-0026); vazio: só ``period``.",
    )
    accumulated: str | None = Field(
        default=None, description="Acumulado: total, running (corrente) ou year (no ano)."
    )
    # Grão somado a partir do publicado (ADR-0013); None: valores publicados.
    grain: str | None = None
    unit: str
    columns: list[ColumnOut]
    rows: list[TableRowOut]
    # Totais da tabela: o território que agrega as linhas (o recorte, ou o Brasil), com o
    # valor publicado pela fonte (não a soma das linhas, que não vale para taxas).
    footer: TableRowOut | None = None
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
    # Correção por índice de preços (ADR-0020), ex.: "ipca", "ipca_grupo".
    correction: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,31}$")
    categories: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Filtro de categorias das dimensões (ex.: c79:2670), como no painel.",
    )
    # Janela de exportação (B5): vários níveis e grãos num arquivo só, em formato longo,
    # com as colunas nivel, grao e tipo (publicado ou derivado). Nunca acumulado (ADR-0026).
    levels: list[str] = Field(
        default_factory=list, max_length=8, description="Níveis (substitui ``level``)."
    )
    grains: list[Grain] = Field(
        default_factory=list,
        max_length=4,
        description="Grãos de tempo (substitui ``grain``); o publicado sai como 'publicado'.",
    )
    format: ExportFormat = "csv"


class HistoryRowOut(_Out):
    """Um período da série completa de um território."""

    period: str
    grain: str
    label: str
    derived: bool = Field(description="Calculado pela regra do KPI (ADR-0013), não publicado.")
    cells: dict[str, CellOut]


class HistoryOut(_Out):
    """Série completa de um território: todos os períodos dos grãos pedidos (B5)."""

    kpi_id: str
    indicator_id: str
    geography: GeographyRefOut
    unit: str
    grains: list[str]
    columns: list[ColumnOut]
    rows: list[HistoryRowOut]
    provenance: Provenance


class PivotFieldOut(_Out):
    """Campo da tabela dinâmica: território, período ou uma dimensão."""

    id: str
    label: str


class PivotHeaderOut(_Out):
    """Uma linha (ou coluna) da tabela dinâmica: um valor por campo."""

    keys: list[str]
    labels: list[str]


class PivotOut(_Out):
    """Tabela dinâmica (B6): linhas e colunas escolhidas; os campos fora dela ficam no
    Total publicado (sem somas novas); nunca acumulada (ADR-0026)."""

    kpi_id: str
    indicator_id: str
    level: str
    grain: str | None = None
    unit: str
    row_fields: list[PivotFieldOut]
    col_fields: list[PivotFieldOut]
    rows: list[PivotHeaderOut]
    columns: list[PivotHeaderOut]
    cells: list[list[CellOut | None]]
    # Linha de totais (território do recorte, ou Brasil), só com Território nas linhas.
    footer: PivotHeaderOut | None = None
    footer_cells: list[CellOut | None] = []
    provenance: Provenance


# ------------------------------------------------------------ métricas de acesso (ADR-0027)


class MetricsPeriodOut(_Out):
    """Período efetivo da consulta (AAAA-MM-DD, as duas pontas incluídas)."""

    from_: str = Field(alias="from", serialization_alias="from")
    to: str

    model_config = ConfigDict(frozen=True, populate_by_name=True)


class MetricsSummaryOut(_Out):
    """Totais do período. Contagens de acessos, nunca de pessoas (sem cookies)."""

    period: MetricsPeriodOut
    generated_at: str
    collection_started_at: str | None = Field(description="Primeiro dia com coleta.")
    views: int
    kpi_opens: int
    downloads: int
    countries: int = Field(description="Países identificados com ao menos um acesso.")
    api_calls: int | None = Field(
        description="null: não coletado (ainda não há API pública). Diferente de zero."
    )


class MetricsGeoItemOut(_Out):
    """Visualizações de um lugar, com supressão abaixo de 5."""

    geography_key: str
    name: str
    views: int | None = Field(description="null quando suprimido (de 1 a 4).")
    share_pct: float | None
    status: Literal["ok", "suprimido", "sem_acessos"]


class MetricsGeoOut(_Out):
    """Visualizações por País, Grande Região ou Estado."""

    level: Literal["pais", "regiao", "uf"]
    within: str | None
    period: MetricsPeriodOut
    items: list[MetricsGeoItemOut]


class MetricsDatasetOut(_Out):
    """Indicador mais acessado (título e tema do release ativo)."""

    kpi_id: str
    title: str
    theme: str
    views: int = Field(description="Aberturas do indicador no painel.")
    downloads: int
    api_calls: int | None


class MetricsDatasetsOut(_Out):
    """Ranking dos indicadores; só entram os com 5 ou mais aberturas."""

    sort: Literal["views", "downloads"]
    period: MetricsPeriodOut
    items: list[MetricsDatasetOut]
