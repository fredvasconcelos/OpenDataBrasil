"""Contratos da Gold das contas públicas (escopo ``contas``; ADR-0030 a 0034, ADR-0036).

Os fatos guardam chaves inteiras para os textos repetidos (favorecido, unidade gestora,
ação, natureza da despesa, autor de emenda): o texto fica nas dimensões. As enumerações
curtas (tipo de transferência, classe do favorecido, situação do território) ficam no
fato como texto, que o Parquet grava por dicionário.

As chaves inteiras valem dentro de um release: o release fixa as versões de todas as
tabelas juntas (§17.4). A chave natural de cada dimensão continua gravada nela.
"""

from __future__ import annotations

import polars as pl

from odb_processing.contracts import Contract
from odb_processing.values import VALUE_DTYPE

S = pl.String()
I32 = pl.Int32()
I64 = pl.Int64()
B = pl.Boolean()
F64 = pl.Float64()
LS = pl.List(pl.String())
DEC = VALUE_DTYPE

DIM_RECIPIENT = Contract(
    name="dim_recipient",
    version="1.1.0",  # 1.1.0: sede do cadastro PJ
    schema={
        "recipient_key": I64,
        "recipient_code": S,
        "recipient_name": S,
        "recipient_class": S,
        "legal_nature_code": S,
        "legal_nature_description": S,
        "cnae_code": S,
        "cnae_description": S,
        "cnae_section_code": S,
        "cnae_section_description": S,
        # Sede no cadastro PJ (texto da fonte): distingue homônimos na tela sem o CNPJ.
        "seat_municipality_name": S,
        "seat_uf": S,
        "is_natural_person": B,
        "in_transfers": B,
        "in_payments": B,
    },
    key=("recipient_key",),
    required=("recipient_key", "recipient_code", "recipient_class", "is_natural_person"),
    partition_by=(),
)

DIM_MANAGEMENT_UNIT = Contract(
    name="dim_management_unit",
    version="1.0.0",
    schema={
        "ug_key": I32,
        "management_unit_code": S,
        "management_unit_name": S,
        "organ_code": S,
        "organ_name": S,
        "superior_organ_code": S,
        "superior_organ_name": S,
        "first_period": S,
        "last_period": S,
    },
    key=("ug_key",),
    required=("ug_key", "first_period", "last_period"),  # código vazio na fonte é chave válida
    partition_by=(),
)

DIM_BUDGET_ACTION = Contract(
    name="dim_budget_action",
    version="1.0.0",
    schema={
        "action_key": I32,
        "fiscal_year": I32,
        "function_code": S,
        "function_name": S,
        "subfunction_code": S,
        "subfunction_name": S,
        "program_code": S,
        "program_name": S,
        "action_code": S,
        "action_name": S,
        "citizen_language": S,
    },
    key=("action_key",),
    required=("action_key", "fiscal_year", "action_code"),
    partition_by=(),
)

DIM_EXPENSE_NATURE = Contract(
    name="dim_expense_nature",
    version="1.0.0",
    schema={
        "nature_key": I32,
        "economic_category_code": S,
        "economic_category_name": S,
        "expense_group_code": S,
        "expense_group_name": S,
        "application_modality_code": S,
        "application_modality_name": S,
        "expense_element_code": S,
        "expense_element_name": S,
    },
    key=("nature_key",),
    required=("nature_key",),
    partition_by=(),
)

DIM_AMENDMENT_AUTHOR = Contract(
    name="dim_amendment_author",
    version="1.0.0",
    schema={"author_key": I32, "amendment_author_code": S, "amendment_author_name": S},
    key=("author_key",),
    required=("author_key",),
    partition_by=(),
)

# Grão: mês x território x tipo x tipo de favorecido x favorecido x UG x ação x natureza.
FACT_FEDERAL_TRANSFER = Contract(
    name="fact_federal_transfer",
    version="1.0.0",
    schema={
        "year": I32,
        "period": S,
        "geography_key": S,
        "uf_code": S,
        "municipality_id": S,
        "territory_status": S,
        "transfer_type": S,
        "recipient_type": S,
        "recipient_class": S,
        "recipient_key": I64,
        "ug_key": I32,
        "action_key": I32,
        "nature_key": I32,
        "value": DEC,
        "source_lines": I32,
    },
    key=(
        "period",
        "geography_key",
        "territory_status",
        "transfer_type",
        "recipient_type",
        "recipient_key",
        "ug_key",
        "action_key",
        "nature_key",
    ),
    required=(
        "year",
        "period",
        "geography_key",
        "territory_status",
        "recipient_key",
        "ug_key",
        "action_key",
        "nature_key",
        "value",
        "source_lines",
    ),
    partition_by=("year",),
)

# Grão: mês x território da sede x favorecido x UG.
FACT_FEDERAL_PAYMENT_RECIPIENT = Contract(
    name="fact_federal_payment_recipient",
    version="1.0.0",
    schema={
        "year": I32,
        "period": S,
        "geography_key": S,
        "uf_code": S,
        "municipality_id": S,
        "territory_status": S,
        "recipient_class": S,
        "recipient_key": I64,
        "ug_key": I32,
        "value": DEC,
        "source_lines": I32,
    },
    key=("period", "geography_key", "territory_status", "recipient_key", "ug_key"),
    required=(
        "year",
        "period",
        "geography_key",
        "territory_status",
        "recipient_key",
        "ug_key",
        "value",
        "source_lines",
    ),
    partition_by=("year",),
)

# Grão: mês x UG x ação x natureza x autor de emenda. Sem território (ADR-0032, decisão 6).
FACT_FEDERAL_BUDGET_EXECUTION = Contract(
    name="fact_federal_budget_execution",
    version="1.0.0",
    schema={
        "year": I32,
        "period": S,
        "ug_key": I32,
        "action_key": I32,
        "nature_key": I32,
        "author_key": I32,
        "committed": DEC,
        "liquidated": DEC,
        "paid": DEC,
        "payables_registered": DEC,
        "payables_cancelled": DEC,
        "payables_paid": DEC,
        "source_lines": I32,
    },
    key=("period", "ug_key", "action_key", "nature_key", "author_key"),
    required=(
        "year",
        "period",
        "ug_key",
        "action_key",
        "nature_key",
        "author_key",
        "committed",
        "liquidated",
        "paid",
        "payables_registered",
        "payables_cancelled",
        "payables_paid",
        "source_lines",
    ),
    partition_by=("year",),
)

# Mapa e gráfico (ADR-0034, decisão 1): total e "detalhar por", por território e mês.
AGG_CONTAS_TERRITORY = Contract(
    name="agg_contas_territory",
    version="1.0.0",
    schema={
        "lens": S,
        "level_id": S,
        "geography_key": S,
        "year": I32,
        "period": S,
        "dimension_id": S,
        "category_code": S,
        "category_label": S,
        "value": DEC,
        "source_lines": I64,
    },
    key=("lens", "geography_key", "period", "dimension_id", "category_code"),
    required=(
        "lens",
        "level_id",
        "geography_key",
        "year",
        "period",
        "dimension_id",
        "category_code",
        "value",
        "source_lines",
    ),
    partition_by=("lens", "level_id"),
)

# Ranking contextual (ADR-0034, decisão 4): os N maiores destinatários por território e ano.
AGG_RECIPIENT_RANK = Contract(
    name="agg_recipient_rank",
    version="1.0.0",
    schema={
        "lens": S,
        "level_id": S,
        "geography_key": S,
        "year": I32,
        "rank": I32,
        "recipient_key": I64,
        "recipient_class": S,
        "value": DEC,
        "source_lines": I64,
        "recipients_in_territory": I64,
    },
    key=("lens", "geography_key", "year", "rank"),
    required=(
        "lens",
        "level_id",
        "geography_key",
        "year",
        "rank",
        "recipient_key",
        "value",
        "recipients_in_territory",
    ),
    partition_by=("lens", "level_id"),
)

# Conferência A x C por mês e ação (ADR-0036, decisão 2).
AGG_TRANSFER_RECONCILIATION = Contract(
    name="agg_transfer_reconciliation",
    version="1.0.0",
    schema={
        "year": I32,
        "period": S,
        "action_code": S,
        "action_name": S,
        "transfer_type": S,
        "value_transfers": DEC,
        "paid_execution": DEC,
        "payables_paid_execution": DEC,
        "shortfall": DEC,
        "action_status": S,
    },
    key=("period", "action_code"),
    required=(
        "year",
        "period",
        "action_code",
        "value_transfers",
        "paid_execution",
        "payables_paid_execution",
        "shortfall",
        "action_status",
    ),
    partition_by=(),
)

# Situação de cada mês por lente: aberto, incompleto ou fechado (ADR-0036, decisão 3).
AGG_CONTAS_PERIOD_STATUS = Contract(
    name="agg_contas_period_status",
    version="1.0.0",
    schema={
        "lens": S,
        "year": I32,
        "period": S,
        "status": S,
        "value": DEC,
        "reference_value": DEC,
        "shortfall": DEC,
        "shortfall_share": F64,
        "missing_actions": LS,
        "note": S,
    },
    key=("lens", "period"),
    required=("lens", "year", "period", "status", "value", "note"),
    partition_by=(),
)

CONTAS_CONTRACTS: tuple[Contract, ...] = (
    DIM_RECIPIENT,
    DIM_MANAGEMENT_UNIT,
    DIM_BUDGET_ACTION,
    DIM_EXPENSE_NATURE,
    DIM_AMENDMENT_AUTHOR,
    FACT_FEDERAL_TRANSFER,
    FACT_FEDERAL_PAYMENT_RECIPIENT,
    FACT_FEDERAL_BUDGET_EXECUTION,
    AGG_CONTAS_TERRITORY,
    AGG_RECIPIENT_RANK,
    AGG_TRANSFER_RECONCILIATION,
    AGG_CONTAS_PERIOD_STATUS,
)
