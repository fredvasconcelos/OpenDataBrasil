"""Observabilidade com OpenTelemetry (plano R-V, etapa V4).

Liga-se só quando ``OTEL_EXPORTER_OTLP_ENDPOINT`` está definido (variáveis padrão do
OpenTelemetry). Sem ela, a API e os testes seguem com os provedores no-op da biblioteca.

- Traces: cada requisição HTTP (instrumentação do FastAPI) e um span por consulta DuckDB.
- Métricas: duração das requisições (FastAPI) e ``odb.duckdb.query.duration`` por tabela.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import AbstractContextManager

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.util.types import AttributeValue

TRACER = trace.get_tracer("odb_api")
METER = metrics.get_meter("odb_api")
DUCKDB_DURATION = METER.create_histogram(
    "odb.duckdb.query.duration",
    unit="s",
    description="Duração de cada consulta DuckDB sobre a Gold do release.",
    # As faixas padrão do SDK são para milissegundos; estas, para segundos.
    explicit_bucket_boundaries_advisory=[
        0.001,
        0.0025,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
    ],
)
DUCKDB_ROWS = METER.create_histogram(
    "odb.duckdb.query.rows",
    unit="{row}",
    description="Linhas devolvidas por consulta DuckDB.",
    explicit_bucket_boundaries_advisory=[1, 10, 100, 1_000, 5_000, 10_000, 50_000, 100_000],
)


def enabled() -> bool:
    """Há um coletor configurado?"""
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))


def setup(app: FastAPI, *, code_version: str, environment: str) -> None:
    """Configura traces e métricas OTLP e instrumenta o FastAPI (uma vez por processo)."""
    if not enabled():
        return
    # Importações só quando ligado: o SDK e os exportadores não pesam nos testes.
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # noqa: PLC0415
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: PLC0415
    from opentelemetry.sdk.metrics import MeterProvider  # noqa: PLC0415
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # noqa: PLC0415
    from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
    from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415

    resource = Resource.create(
        {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "odb-api"),
            "service.version": code_version,
            "deployment.environment.name": environment,
            # Cada worker do uvicorn é um processo: distingue as séries de métricas.
            "service.instance.id": f"{os.uname().nodename}-{os.getpid()}",
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15_000)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")


def duckdb_span(tables: Mapping[str, str], release_id: str) -> AbstractContextManager[trace.Span]:
    """Span de uma consulta DuckDB; ``tables`` mapeia apelido → tabela Gold."""
    return TRACER.start_as_current_span(
        "duckdb.query",
        kind=trace.SpanKind.CLIENT,
        attributes={
            "db.system.name": "duckdb",
            "odb.tables": sorted(set(tables.values())),
            "odb.release_id": release_id,
        },
    )


def record_query(tables: Mapping[str, str], seconds: float, rows: int, *, truncated: bool) -> None:
    """Registra duração e linhas da consulta (a tabela principal vira atributo)."""
    attrs: dict[str, AttributeValue] = {
        "odb.table": min(tables.values()) if tables else "-",
        "odb.truncated": truncated,
    }
    DUCKDB_DURATION.record(seconds, attrs)
    DUCKDB_ROWS.record(rows, attrs)
