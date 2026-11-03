"""Conector da API SIDRA do IBGE (``https://apisidra.ibge.gov.br/values``).

Comportamentos verificados por requisição real em 2026-11-03 (fixtures em
``tests/fixtures/ibge/sidra``):

* a resposta é uma lista JSON em que o primeiro elemento é o cabeçalho, que
  rotula as colunas ``NC, NN, MC, MN, V, D1C, D1N, ...``;
* um período inexistente retorna **HTTP 200 só com o cabeçalho**. Por isso o
  ``validate_raw`` exige ao menos uma observação;
* uma tabela inexistente retorna HTTP 400 com texto simples;
* não há ``ETag`` nem ``Last-Modified`` (``cache-control: no-cache``). A
  detecção de mudanças é por checksum de cada partição;
* o limite documentado é de 100.000 valores por consulta. O plano divide por
  período e falha se a estimativa por período passar do limite.

A divisão é sempre por período, numa requisição por período. Os períodos
recentes (``refresh_recent_periods``) são baixados de novo a cada execução,
porque períodos antigos podem ser revisados (§7.6).
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from odb_ingestion.config import ConfigError, DatasetConfig
from odb_ingestion.contract import (
    BaseConnector,
    Capability,
    ExtractionPlan,
    ExtractionRequest,
    HealthStatus,
    ValidationResult,
    Watermark,
)
from odb_ingestion.http import DownloadResult, HttpClient, HttpError

SIDRA_VALUE_LIMIT = 100_000
_LEVEL = re.compile(r"^n([1-9]|1[0-9]|[1-9][0-9]{2,3})$")
_DIM = re.compile(r"^D[1-9]$")
_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")
# Símbolos especiais de valor citados na documentação do SIDRA. O significado é
# classificado na Silver (§9.4). Aqui o símbolo só é contado.
KNOWN_SYMBOLS = frozenset({"-", "..", "...", "X"})
_HEADER_KEYS = ("NC", "NN", "MC", "MN", "V")


class SidraParams(BaseModel):
    """Parâmetros de um dataset SIDRA (``[datasets.params]``)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    table: str = Field(pattern=r"^\d{1,6}$")
    variables: tuple[str, ...] = Field(min_length=1)
    territorial_level: str
    classifications: dict[str, str] = Field(default_factory=dict)
    period_discovery_level: str = "n1"
    territory_dimension: str = "D1"
    variable_dimension: str = "D2"
    period_dimension: str = "D3"
    estimated_values_per_period: int = Field(ge=1)
    min_rows: int = Field(default=1, ge=1)
    max_rows: int | None = Field(default=None, ge=1)
    refresh_recent_periods: int = Field(default=2, ge=0)
    max_bytes: int = Field(default=50 * 1024**2, ge=1)

    @field_validator("variables")
    @classmethod
    def _vars(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for v in value:
            if not re.fullmatch(r"^\d{1,8}$", v):
                msg = f"variável SIDRA inválida: {v!r}"
                raise ValueError(msg)
        return value

    @field_validator("territorial_level", "period_discovery_level")
    @classmethod
    def _level(cls, value: str) -> str:
        if not _LEVEL.fullmatch(value):
            msg = f"nível territorial SIDRA inválido: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("territory_dimension", "variable_dimension", "period_dimension")
    @classmethod
    def _dim(cls, value: str) -> str:
        if not _DIM.fullmatch(value):
            msg = f"dimensão SIDRA inválida: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("classifications")
    @classmethod
    def _classes(cls, value: dict[str, str]) -> dict[str, str]:
        for key, cats in value.items():
            if not re.fullmatch(r"^c\d{1,6}$", key) or not re.fullmatch(
                r"^(all|\d+(,\d+)*)$", cats
            ):
                msg = f"classificação SIDRA inválida: {key}={cats}"
                raise ValueError(msg)
        return value

    @property
    def level_code(self) -> str:
        """Código numérico do nível (``n6`` → ``6``)."""
        return self.territorial_level[1:]


class SidraConnector(BaseConnector):
    """Conector SIDRA: uma partição por período."""

    connector_type: ClassVar[str] = "sidra"
    capabilities: ClassVar[frozenset[Capability]] = frozenset(
        {
            Capability.DISCOVER_CONFIGURED,
            Capability.PARTITIONED,
            Capability.INCREMENTAL_CHECKSUM,
            Capability.HEALTHCHECK,
        }
    )

    def validate_params(self, dataset: DatasetConfig) -> None:
        """Valida os parâmetros e o limite de 100 mil valores por requisição."""
        params = self.params(dataset)
        if params.estimated_values_per_period > SIDRA_VALUE_LIMIT:
            msg = (
                f"{dataset.id}: estimativa de {params.estimated_values_per_period} valores por "
                f"período excede o limite do SIDRA ({SIDRA_VALUE_LIMIT})"
            )
            raise ConfigError(msg)

    @staticmethod
    def params(dataset: DatasetConfig) -> SidraParams:
        """Parâmetros tipados de um dataset."""
        try:
            return SidraParams.model_validate(dataset.params)
        except ValidationError as exc:
            msg = f"{dataset.id}: parâmetros SIDRA inválidos: {exc}"
            raise ConfigError(msg) from exc

    # ------------------------------------------------------------- URLs

    def _values_url(self, params: SidraParams, level: str, variables: str, period: str) -> str:
        path = f"/values/t/{params.table}/{level}/all/v/{variables}/p/{period}"
        for key, cats in sorted(params.classifications.items()):
            path += f"/{key}/{cats}"
        return self.source.base_url.rstrip("/") + path

    def discover_periods(self, dataset: DatasetConfig, http: HttpClient) -> list[str]:
        """Períodos disponíveis, consultados no nível de descoberta (por padrão, Brasil)."""
        params = self.params(dataset)
        url = self._values_url(params, params.period_discovery_level, params.variables[0], "all")
        try:
            payload = json.loads(http.get_bytes(url))
        except json.JSONDecodeError as exc:
            msg = f"{url}: resposta de descoberta de períodos não é JSON"
            raise HttpError(msg, url=url) from exc
        if not isinstance(payload, list) or len(payload) < 2:  # noqa: PLR2004
            msg = f"{url}: nenhum período retornado"
            raise HttpError(msg, url=url)
        key = f"{params.period_dimension}C"
        periods = sorted(
            {str(row[key]) for row in payload[1:] if isinstance(row, dict) and key in row}
        )
        if not periods:
            msg = f"{url}: dimensão de período {key} ausente"
            raise HttpError(msg, url=url)
        return periods

    # ------------------------------------------------------------- contrato

    def plan(
        self, dataset_id: str, http: HttpClient, watermark: Watermark, *, full: bool = False
    ) -> ExtractionPlan:
        """Uma requisição por período novo, recente ou (com ``full``) todos."""
        dataset = self.describe(dataset_id)
        params = self.params(dataset)
        periods = self.discover_periods(dataset, http)
        recent = (
            set(periods[-params.refresh_recent_periods :])
            if params.refresh_recent_periods
            else set()
        )
        requests: list[ExtractionRequest] = []
        skipped: list[str] = []
        for period in periods:
            key = f"p{period}"
            if full or key not in watermark.partitions or period in recent:
                requests.append(
                    ExtractionRequest(
                        partition_key=key,
                        url=self._values_url(
                            params, params.territorial_level, ",".join(params.variables), period
                        ),
                        artifact_name=f"t{params.table}-{params.territorial_level}-p{period}.json",
                        reference_period=period,
                        max_bytes=params.max_bytes,
                    )
                )
            else:
                skipped.append(period)
        notes = [f"períodos disponíveis: {len(periods)}"]
        if skipped:
            notes.append(f"períodos já ingeridos e fora da janela de revisão: {skipped}")
        return ExtractionPlan(
            dataset_id=dataset_id,
            requests=tuple(requests),
            notes=tuple(notes),
            metadata={"available_periods": periods, "refresh_recent_periods": sorted(recent)},
        )

    def validate_raw(  # noqa: PLR0911, PLR0912 - verificações sequenciais e independentes
        self, dataset_id: str, request: ExtractionRequest, result: DownloadResult
    ) -> ValidationResult:
        """Estrutura, nível, período, variáveis, contagem e unicidade das observações."""
        params = self.params(self.describe(dataset_id))
        if result.path is None:
            return ValidationResult(errors=("artefato sem conteúdo",))
        try:
            payload = json.loads(result.path.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return ValidationResult(errors=(f"JSON inválido: {exc}",))
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            return ValidationResult(errors=("formato inesperado: lista com cabeçalho esperada",))
        header: dict[str, Any] = payload[0]
        rows = payload[1:]
        errors: list[str] = []
        warnings: list[str] = []
        dims = (params.territory_dimension, params.variable_dimension, params.period_dimension)
        required = [*_HEADER_KEYS, *(f"{d}C" for d in dims)]
        missing = [k for k in required if k not in header]
        if missing:
            return ValidationResult(errors=(f"cabeçalho sem as colunas {missing}",))
        if not rows:
            return ValidationResult(
                errors=("resposta sem observações (período inexistente ou consulta vazia)",)
            )
        keys = set(header)
        bad_shape = sum(1 for r in rows if not isinstance(r, dict) or set(r) != keys)
        if bad_shape:
            return ValidationResult(
                errors=(f"{bad_shape} linhas com colunas diferentes do cabeçalho",)
            )

        if len(rows) < params.min_rows:
            errors.append(f"{len(rows)} observações, mínimo esperado {params.min_rows}")
        if params.max_rows is not None and len(rows) > params.max_rows:
            errors.append(f"{len(rows)} observações, máximo esperado {params.max_rows}")
        levels = Counter(r["NC"] for r in rows)
        if set(levels) != {params.level_code}:
            errors.append(f"níveis territoriais inesperados: {dict(levels)}")
        period_key = f"{params.period_dimension}C"
        periods = Counter(r[period_key] for r in rows)
        if set(periods) != {request.reference_period}:
            errors.append(f"períodos inesperados: {dict(periods)}")
        var_key = f"{params.variable_dimension}C"
        variables = set(Counter(r[var_key] for r in rows))
        if variables != set(params.variables):
            errors.append(
                f"variáveis {sorted(variables)} diferem das esperadas {list(params.variables)}"
            )

        dim_keys = sorted(k for k in keys if re.fullmatch(r"D\d+C", k))
        identities = Counter(tuple(r[k] for k in dim_keys) for r in rows)
        duplicated = sum(1 for n in identities.values() if n > 1)
        if duplicated:
            errors.append(f"{duplicated} combinações de dimensões duplicadas")

        values = Counter(
            "numeric" if _NUMERIC.fullmatch(str(r["V"])) else str(r["V"]) for r in rows
        )
        symbols = {k: n for k, n in values.items() if k != "numeric"}
        unknown = {k: n for k, n in symbols.items() if k not in KNOWN_SYMBOLS}
        if unknown:
            warnings.append(f"símbolos de valor não catalogados: {unknown}")
        stats = {
            "observations": len(rows),
            "territories": len({r[f"{params.territory_dimension}C"] for r in rows}),
            "variables": sorted(variables),
            "dimensions": dim_keys,
            "numeric_values": values.get("numeric", 0),
            "special_values": symbols,
            "units": sorted({str(r["MN"]) for r in rows}),
        }
        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings), stats=stats)

    def healthcheck(self, http: HttpClient) -> HealthStatus:
        """Consulta mínima (último período, nível Brasil) do primeiro dataset."""
        datasets = self.discover()
        if not datasets:
            return HealthStatus(ok=False, detail="nenhum dataset configurado")
        params = self.params(datasets[0])
        url = self._values_url(params, "n1", params.variables[0], "last")
        started = time.perf_counter()
        try:
            body = json.loads(http.get_bytes(url))
        except (HttpError, json.JSONDecodeError) as exc:
            return HealthStatus(ok=False, detail=f"{type(exc).__name__}: {exc}")
        latency = round((time.perf_counter() - started) * 1000, 1)
        ok = isinstance(body, list) and len(body) >= 2  # noqa: PLR2004
        return HealthStatus(
            ok=ok, detail=f"{url} → {len(body) - 1} observação(ões)", latency_ms=latency
        )
