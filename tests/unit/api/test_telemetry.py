"""Instrumentação OpenTelemetry da API (plano R-V, etapa V4)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from odb_api import telemetry

_EXPORTER = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def _provider() -> None:
    # O provedor global só pode ser definido uma vez por processo.
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))
    trace.set_tracer_provider(provider)


def test_desligada_sem_coletor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert not telemetry.enabled()
    app = FastAPI()
    telemetry.setup(app, code_version="x", environment="test")  # não instrumenta
    assert not getattr(app, "_is_instrumented_by_opentelemetry", False)


def test_span_da_consulta_duckdb() -> None:
    _EXPORTER.clear()
    tabelas = {"obs": "indicator_observation", "geo": "dim_geography"}
    with telemetry.duckdb_span(tabelas, "r1") as span:
        span.set_attribute("odb.rows", 27)
    telemetry.record_query(tabelas, 0.012, 27, truncated=False)  # no-op sem MeterProvider
    (feito,) = _EXPORTER.get_finished_spans()
    assert feito.name == "duckdb.query"
    assert feito.attributes is not None
    assert feito.attributes["db.system.name"] == "duckdb"
    assert feito.attributes["odb.tables"] == ("dim_geography", "indicator_observation")
    assert feito.attributes["odb.release_id"] == "r1"
    assert feito.attributes["odb.rows"] == 27
