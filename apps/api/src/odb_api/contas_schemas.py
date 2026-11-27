"""Modelos de resposta do bloco de contas públicas (``/api/v1/contas``, ADR-0037).

Na tela aparecem só os nomes (ADR-0034, decisão 6): nenhuma resposta traz CNPJ, CPF
mascarado ou código SIAFI do favorecido. O favorecido é identificado por ``recipient_id``,
estável entre releases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from odb_api.schemas import TableVersionOut

Lens = Literal["A", "B"]


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class PeriodStatusOut(_Out):
    """Situação de um mês numa lente (ADR-0036, decisão 3)."""

    period: str
    status: Literal["aberto", "incompleto", "fechado"]
    note: str
    shortfall_share: float | None = None
    missing_actions: list[str] = Field(default_factory=list)


class ContasProvenance(_Out):
    """Release, tabelas e meses usados; ``partial`` quando algum mês não está fechado."""

    release_id: str
    tables: list[TableVersionOut]
    periods: list[str]
    partial: bool
    period_notes: list[PeriodStatusOut] = Field(default_factory=list)


class ContasDimensionOut(_Out):
    """Dimensão do "detalhar por" ou do agrupamento da tabela."""

    id: str
    label: str


class LensOut(_Out):
    """Lente de dados e o que ela oferece."""

    lens: Literal["A", "B", "C"]
    label: str
    description: str
    notes: list[str]
    dimensions: list[ContasDimensionOut]
    group_by: list[ContasDimensionOut]
    periods: list[str]
    latest_period: str | None
    statuses: list[PeriodStatusOut]


class ContasMetaOut(_Out):
    """Lentes, dimensões, meses e classes de favorecido do release."""

    release_id: str
    lenses: list[LensOut]
    recipient_classes: dict[str, str]
    notes: list[str]


class MapRowOut(_Out):
    """Total de um território."""

    geography_key: str
    name: str
    value: float


class ContasMapOut(_Out):
    """Mapa: só o total por território (ADR-0034, decisão 1)."""

    lens: Lens
    level: str
    within: str | None
    dimension: str | None
    categories: list[str]
    unit: str = "R$ (valores nominais)"
    total: float
    rows: list[MapRowOut]
    provenance: ContasProvenance


class CompositionRowOut(_Out):
    """Categoria do "detalhar por" num território."""

    category_code: str
    label: str
    value: float
    share: float | None


class ContasCompositionOut(_Out):
    """Composição do território: as maiores categorias e "demais"."""

    lens: Lens
    geography_key: str
    dimension: str
    total: float
    rows: list[CompositionRowOut]
    provenance: ContasProvenance


class SeriesPointOut(_Out):
    """Valor de um período."""

    period: str
    value: float


class SeriesLineOut(_Out):
    """Série de uma categoria (ou do total)."""

    category_code: str
    label: str
    points: list[SeriesPointOut]


class ContasSeriesOut(_Out):
    """Série mensal ou anual (ADR-0034, decisão 2)."""

    lens: Lens
    geography_key: str
    grain: Literal["mes", "ano"]
    dimension: str | None
    lines: list[SeriesLineOut]
    provenance: ContasProvenance


class RecipientRefOut(_Out):
    """Favorecido como aparece na tela: nome, sede e classe (sem código)."""

    recipient_id: str
    name: str | None
    seat_municipality: str | None
    seat_uf: str | None
    recipient_class: str
    class_label: str
    is_natural_person: bool


class RankingRowOut(_Out):
    """Posição no ranking."""

    rank: int
    recipient: RecipientRefOut
    value: float


class ContasRankingOut(_Out):
    """Maiores destinatários do território no ano (ADR-0034, decisão 4)."""

    lens: Lens
    geography_key: str
    year: int
    page: int
    page_size: int
    pages: int
    total_recipients: int
    rows: list[RankingRowOut]
    notes: list[str]
    provenance: ContasProvenance


class ContasTableRowOut(_Out):
    """Linha da tabela: um grupo (território, categoria ou favorecido)."""

    key: str
    label: str
    value: float
    share: float | None
    recipient: RecipientRefOut | None = None


class ContasTableOut(_Out):
    """Tabela paginada no servidor, 10 linhas por página (ADR-0034, decisão 3)."""

    lens: Lens
    geography_key: str
    group_by: str
    filters: list[str]
    sort: Literal["value", "name"]
    page: int
    page_size: int
    pages: int
    rows_total: int
    value_total: float
    page_value: float
    rows: list[ContasTableRowOut]
    notes: list[str]
    provenance: ContasProvenance


class LensTotalOut(_Out):
    """Total de uma lente num ano."""

    lens: Lens
    year: int
    value: float


class OrganTotalOut(_Out):
    """Órgão pagador ou concedente."""

    lens: Lens
    organ: str | None
    value: float


class LensPointOut(_Out):
    """Valor mensal de uma lente."""

    lens: Lens
    period: str
    value: float


class RecipientProfileOut(_Out):
    """Ficha do favorecido (ADR-0031: aviso de homônimo e ``noindex`` para PF)."""

    recipient: RecipientRefOut
    legal_nature: str | None
    economic_activity: str | None
    economic_section: str | None
    totals: list[LensTotalOut]
    organs: list[OrganTotalOut]
    series: list[LensPointOut]
    notes: list[str]
    provenance: ContasProvenance


class SearchHitOut(_Out):
    """Resultado da busca."""

    kind: Literal["favorecido", "orgao", "programa", "acao"]
    id: str
    label: str
    detail: str | None = None


class ContasSearchOut(_Out):
    """Busca por favorecido PJ, órgão, programa e ação (plano, seção 9)."""

    q: str
    hits: list[SearchHitOut]
    release_id: str


class ExecutionRowOut(_Out):
    """Fases da despesa de uma categoria (nunca somadas entre si)."""

    category_code: str
    label: str
    committed: float
    liquidated: float
    paid: float
    payables_registered: float
    payables_cancelled: float
    payables_paid: float


class ContasExecutionOut(_Out):
    """Execução da despesa (lente C), sem território (ADR-0032, decisão 6)."""

    dimension: str
    page: int
    page_size: int
    pages: int
    rows_total: int
    total: ExecutionRowOut
    rows: list[ExecutionRowOut]
    provenance: ContasProvenance
