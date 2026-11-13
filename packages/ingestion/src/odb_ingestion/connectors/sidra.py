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
* o limite efetivo é de 50.000 valores por consulta (a ajuda cita 100.000, mas
  a API recusou 67.236 valores com HTTP 400 em 2026-11-04). O plano divide por
  período e falha se a estimativa por requisição passar do limite;
* classificações entram como ``/c<id>/<categorias>``. Uma classificação que não
  pertence à tabela gera HTTP 400 ("incompatível com a tabela"), o que serve de
  validação dos códigos configurados.

A divisão é por período, numa requisição por período. Com ``split_by_variable``,
cada variável vai em requisição própria; com ``split_by_classification``, cada
categoria da classificação indicada (tabelas com classificações cruzadas passam
do limite no nível municipal, por exemplo a 9718). Os períodos recentes
(``refresh_recent_periods``) são baixados de novo a cada execução, porque
períodos antigos podem ser revisados (§7.6).
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

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

# A ajuda da API cita 100.000 valores, mas a API respondeu HTTP 400 "Quantidade de
# valores solicitados: 67236 excedeu o limite: 50000" em 2026-11-04.
SIDRA_VALUE_LIMIT = 50_000
_LEVEL = re.compile(r"^n([1-9]|1[0-9]|[1-9][0-9]{2,3})$")
_DIM = re.compile(r"^D[1-9]$")
_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")
# Símbolos especiais de valor citados na documentação do SIDRA. O significado é
# classificado na Silver (§9.4). Aqui o símbolo só é contado.
KNOWN_SYMBOLS = frozenset({"-", "..", "...", "X"})
_HEADER_KEYS = ("NC", "NN", "MC", "MN", "V")


@dataclass(frozen=True, slots=True)
class RequestGroup:
    """Variáveis e classificações de uma requisição de um período."""

    variables: tuple[str, ...]
    classifications: dict[str, str]
    suffix: str
    # Níveis territoriais da requisição (vazio: os do dataset).
    levels: tuple[str, ...] = ()


class SidraParams(BaseModel):
    """Parâmetros de um dataset SIDRA (``[datasets.params]``)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    table: str = Field(pattern=r"^\d{1,6}$")
    variables: tuple[str, ...] = Field(min_length=1)
    territorial_levels: tuple[str, ...] = Field(min_length=1)
    classifications: dict[str, str] = Field(default_factory=dict)
    period_discovery_level: str = "n1"
    territory_dimension: str = "D1"
    variable_dimension: str = "D2"
    period_dimension: str = "D3"
    # Estimativa, mínimo e máximo valem por requisição: por período ou, com
    # ``split_by_variable``, por período e variável.
    estimated_values_per_period: int = Field(ge=1)
    split_by_variable: bool = False
    # Classificações cujas categorias (listadas em ``classifications``) vão em
    # requisições separadas. Com várias, cada combinação de categorias é uma requisição.
    split_by_classification: tuple[str, ...] = ()
    min_rows: int = Field(default=1, ge=1)
    max_rows: int | None = Field(default=None, ge=1)
    refresh_recent_periods: int = Field(default=2, ge=0)
    max_bytes: int = Field(default=50 * 1024**2, ge=1)
    # Tipo dos períodos da tabela (descritor: TipoPeriodo). Códigos SIDRA: ano
    # "AAAA", mês "AAAAMM", trimestre "AAAATT" (01 a 04).
    # Detalhe só em alguns níveis: a classificação ``detail_classification`` vem
    # inteira (categorias listadas em ``classifications``) só em ``detail_levels``;
    # nos demais níveis, só o Total (``detail_total``). Evita multiplicar as
    # requisições municipais pelo número de categorias.
    detail_classification: str | None = Field(default=None, pattern=r"^c\d{1,6}$")
    detail_total: str | None = Field(default=None, pattern=r"^\d+$")
    detail_levels: tuple[str, ...] = ()
    # Detalhes marginais (ADR-0016): cada conjunto troca as categorias de
    # ``classifications`` e vira uma requisição própria por período (sufixo
    # ``-x<classificação>``, a última do conjunto, que é a detalhada). Usado para
    # trazer outra classificação inteira com as demais no Total, sem pedir os
    # cruzamentos. As categorias do conjunto não repetem o Total
    # da classificação detalhada, que já vem na requisição principal.
    extra_sets: tuple[dict[str, str], ...] = ()
    # Níveis das requisições extras (vazio: os do dataset).
    extra_levels: tuple[str, ...] = ()
    # Níveis de cada conjunto extra, quando a fonte só publica a classificação em alguns
    # (nota da tabela: "disponível apenas para o nível territorial Brasil"). Vazio no
    # conjunto: vale ``extra_levels``.
    extra_set_levels: tuple[tuple[str, ...], ...] = ()
    # Categorias por requisição nos grupos que pedem municípios (n6), quando a lista
    # inteira passaria do limite de valores da API (ponto 7 do relatório de
    # 2026-11-12). A lista é dividida em lotes na ordem declarada, com sufixo -k<n>;
    # grupos só até UF não são divididos.
    category_chunk: int | None = Field(default=None, ge=1)
    period_type: Literal["ano", "mes", "trimestre"] = "ano"
    # Meses ou trimestres do mesmo ano numa única requisição (partição "p<ano>").
    # Com isso, ``estimated_values_per_period``, ``min_rows`` e ``max_rows`` valem
    # por requisição (todos os períodos do ano).
    group_periods_by_year: bool = False

    @field_validator("variables")
    @classmethod
    def _vars(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for v in value:
            if not re.fullmatch(r"^\d{1,8}$", v):
                msg = f"variável SIDRA inválida: {v!r}"
                raise ValueError(msg)
        return value

    @field_validator("period_discovery_level")
    @classmethod
    def _level(cls, value: str) -> str:
        if not _LEVEL.fullmatch(value):
            msg = f"nível territorial SIDRA inválido: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("territorial_levels")
    @classmethod
    def _levels(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for level in value:
            cls._level(level)
        if len(set(value)) != len(value):
            msg = f"níveis territoriais repetidos: {value}"
            raise ValueError(msg)
        return tuple(sorted(value, key=lambda lv: int(lv[1:])))

    @field_validator("territory_dimension", "variable_dimension", "period_dimension")
    @classmethod
    def _dim(cls, value: str) -> str:
        if not _DIM.fullmatch(value):
            msg = f"dimensão SIDRA inválida: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("split_by_classification", mode="before")
    @classmethod
    def _split_list(cls, value: object) -> object:
        return (value,) if isinstance(value, str) else value

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

    @model_validator(mode="after")
    def _detail(self) -> SidraParams:
        if not self.detail_levels:
            return self
        cid, total = self.detail_classification, self.detail_total
        listed = self.classifications.get(cid or "", "")
        if cid is None or total is None or listed in ("", "all"):
            msg = "detail_levels exige detail_classification, detail_total e as categorias listadas"
            raise ValueError(msg)
        if total not in listed.split(","):
            msg = f"detail_total {total} fora das categorias listadas de {cid}"
            raise ValueError(msg)
        extra = sorted(set(self.detail_levels) - set(self.territorial_levels))
        if extra or self.split_by_classification:
            msg = "detail_levels precisa ser subconjunto dos níveis e não combina com divisão"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _grouping(self) -> SidraParams:
        if self.group_periods_by_year and self.period_type == "ano":
            msg = "group_periods_by_year exige period_type mes ou trimestre"
            raise ValueError(msg)
        return self

    def period_valid(self, period: str) -> bool:
        """O código do período tem o formato do tipo declarado."""
        if self.period_type == "ano":
            return bool(re.fullmatch(r"\d{4}", period))
        if self.period_type == "mes":
            return bool(re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", period))
        return bool(re.fullmatch(r"\d{4}0[1-4]", period))

    def period_units(self, periods: Sequence[str]) -> list[tuple[str, list[str]]]:
        """Unidades de requisição: (chave do período na partição, códigos SIDRA)."""
        if not self.group_periods_by_year:
            return [(p, [p]) for p in periods]
        by_year: dict[str, list[str]] = {}
        for p in periods:
            by_year.setdefault(p[:4], []).append(p)
        return sorted(by_year.items())

    @model_validator(mode="after")
    def _split(self) -> SidraParams:
        if len(set(self.split_by_classification)) != len(self.split_by_classification):
            msg = (
                f"classificação repetida em split_by_classification: {self.split_by_classification}"
            )
            raise ValueError(msg)
        for cid in self.split_by_classification:
            cats = self.classifications.get(cid)
            if cats is None or cats == "all":
                msg = f"split_by_classification={cid} exige as categorias listadas"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _extras(self) -> SidraParams:
        if not self.extra_sets:
            if self.extra_levels:
                msg = "extra_levels exige extra_sets"
                raise ValueError(msg)
            return self
        if self.split_by_classification:
            msg = "extra_sets não combina com split_by_classification"
            raise ValueError(msg)
        detailed = [list(extra)[-1] for extra in self.extra_sets if extra]
        if len(set(detailed)) != len(detailed):
            msg = f"extra_sets com a mesma classificação detalhada: {detailed}"
            raise ValueError(msg)
        for extra in self.extra_sets:
            # A classificação detalhada pode não estar em ``classifications``: a
            # requisição principal a deixa no Total padrão da API.
            bad = sorted(
                c for c, cats in extra.items() if not re.fullmatch(r"c\d{1,6}", c) or not cats
            )
            if bad:
                msg = f"extra_sets com classificações inválidas: {bad}"
                raise ValueError(msg)
        if self.extra_set_levels and len(self.extra_set_levels) != len(self.extra_sets):
            msg = "extra_set_levels precisa de um item por conjunto de extra_sets"
            raise ValueError(msg)
        outside = sorted(
            {*self.extra_levels, *(lv for lvls in self.extra_set_levels for lv in lvls)}
            - set(self.territorial_levels)
        )
        if outside:
            msg = f"extra_levels fora dos níveis do dataset: {outside}"
            raise ValueError(msg)
        return self

    @property
    def level_codes(self) -> frozenset[str]:
        """Códigos numéricos dos níveis (``n6`` → ``6``), como aparecem na coluna ``NC``."""
        return frozenset(level[1:] for level in self.territorial_levels)

    @property
    def level_signature(self) -> str:
        """Assinatura dos níveis consultados (por exemplo, ``n1n2n3n6``)."""
        return "".join(self.territorial_levels)

    def request_groups(self) -> list[RequestGroup]:
        """Requisições de um período, conforme a divisão configurada.

        Sem divisão, uma requisição. ``split_by_variable`` gera uma por
        variável; ``split_by_classification`` gera uma por combinação de
        categorias das classificações indicadas (as categorias precisam estar
        listadas), na ordem declarada.
        """
        variable_groups = (
            [(v,) for v in self.variables] if self.split_by_variable else [self.variables]
        )
        combos: list[tuple[tuple[str, str], ...]] = [()]
        for cid in self.split_by_classification:
            cats = self.classifications[cid].split(",")
            combos = [(*combo, (cid, cat)) for combo in combos for cat in cats]
        groups: list[RequestGroup] = []
        for variables in variable_groups:
            for combo in combos:
                suffix = f"-v{variables[0]}" if self.split_by_variable else ""
                classes = dict(self.classifications)
                for cid, cat in combo:
                    suffix += f"-{cid}-{cat}"
                    classes[cid] = cat
                if self.detail_levels and self.detail_classification and self.detail_total:
                    cid = self.detail_classification
                    rest = [c for c in classes[cid].split(",") if c != self.detail_total]
                    groups.append(
                        RequestGroup(variables, {**classes, cid: self.detail_total}, suffix + "-t")
                    )
                    groups.append(
                        RequestGroup(
                            variables,
                            {**classes, cid: ",".join(rest)},
                            suffix + "-d",
                            self.detail_levels,
                        )
                    )
                else:
                    groups.append(RequestGroup(variables, classes, suffix))
            base = f"-v{variables[0]}" if self.split_by_variable else ""
            for n, extra in enumerate(self.extra_sets):
                # Sufixo pela classificação detalhada (a última do conjunto), e não pela
                # posição: incluir ou tirar um conjunto não muda as partições dos outros.
                own = self.extra_set_levels[n] if self.extra_set_levels else ()
                groups.append(
                    RequestGroup(
                        variables,
                        {**self.classifications, **extra},
                        f"{base}-x{list(extra)[-1]}",
                        own or self.extra_levels,
                    )
                )
        return self._chunked(groups) if self.category_chunk else groups

    def _chunked(self, groups: list[RequestGroup]) -> list[RequestGroup]:
        """Divide em lotes a lista de categorias dos grupos que pedem municípios."""
        size = self.category_chunk or 0
        out: list[RequestGroup] = []
        for group in groups:
            levels = group.levels or self.territorial_levels
            lists = {c: v.split(",") for c, v in group.classifications.items() if "," in v}
            if "n6" not in levels or not lists:
                out.append(group)
                continue
            cid, cats = max(lists.items(), key=lambda kv: len(kv[1]))
            if len(cats) <= size:
                out.append(group)
                continue
            for n, start in enumerate(range(0, len(cats), size), start=1):
                out.append(
                    RequestGroup(
                        group.variables,
                        {**group.classifications, cid: ",".join(cats[start : start + size])},
                        f"{group.suffix}-k{n}",
                        group.levels,
                    )
                )
        return out

    def partition_key(self, period: str, group: RequestGroup | None = None) -> str:
        """Chave de partição; inclui os níveis (mudar os níveis gera partições novas).

        Com divisão, o sufixo do grupo entra na chave (``n1n2n3n6-p2022-v350-c2661-12869``).
        """
        if group is None:
            if self.split_by_variable or self.split_by_classification:
                msg = "a divisão configurada exige o grupo na chave de partição"
                raise ValueError(msg)
            group = self.request_groups()[0]
        return f"{self.level_signature}-p{period}{group.suffix}"

    def partition_pattern(self) -> re.Pattern[str]:
        """Padrão das chaves de partição vigentes para esta configuração."""
        base = re.escape(self.level_signature) + r"-p(?P<period>[0-9A-Za-z]+)"
        suffixes = "|".join(re.escape(g.suffix) for g in self.request_groups())
        return re.compile(rf"^{base}(?P<suffix>{suffixes})$")

    def request_group(self, partition_key: str) -> RequestGroup:
        """Grupo (variáveis e classificações) de uma partição."""
        match = self.partition_pattern().fullmatch(partition_key)
        if match is None:
            msg = f"chave de partição fora da configuração atual: {partition_key}"
            raise ValueError(msg)
        return next(g for g in self.request_groups() if g.suffix == match["suffix"])

    def request_variables(self, partition_key: str) -> tuple[str, ...]:
        """Variáveis esperadas na resposta de uma partição."""
        return self.request_group(partition_key).variables


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
        """Valida os parâmetros e o limite de valores por requisição."""
        params = self.params(dataset)
        if params.estimated_values_per_period > SIDRA_VALUE_LIMIT:
            msg = (
                f"{dataset.id}: estimativa de {params.estimated_values_per_period} valores por "
                f"requisição excede o limite do SIDRA ({SIDRA_VALUE_LIMIT}); "
                "considere split_by_variable ou split_by_classification"
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

    def _values_url(
        self,
        params: SidraParams,
        levels: tuple[str, ...],
        variables: str,
        period: str,
        classifications: dict[str, str] | None = None,
    ) -> str:
        territory = "/".join(f"{level}/all" for level in levels)
        path = f"/values/t/{params.table}/{territory}/v/{variables}/p/{period}"
        chosen = params.classifications if classifications is None else classifications
        for key, cats in sorted(chosen.items()):
            path += f"/{key}/{cats}"
        return self.source.base_url.rstrip("/") + path

    def discover_periods(self, dataset: DatasetConfig, http: HttpClient) -> list[str]:
        """Períodos disponíveis, consultados no nível de descoberta (por padrão, Brasil)."""
        params = self.params(dataset)
        url = self._values_url(params, (params.period_discovery_level,), params.variables[0], "all")
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
        """Uma requisição por período (e variável, se dividido) novo, recente ou todos."""
        dataset = self.describe(dataset_id)
        params = self.params(dataset)
        periods = self.discover_periods(dataset, http)
        invalid = [p for p in periods if not params.period_valid(p)]
        if invalid:
            msg = f"{dataset_id}: períodos fora do formato '{params.period_type}': {invalid[:5]}"
            raise ConfigError(msg)
        units = params.period_units(periods)
        recent = (
            {key for key, _ in units[-params.refresh_recent_periods :]}
            if params.refresh_recent_periods
            else set()
        )
        requests: list[ExtractionRequest] = []
        skipped: list[str] = []
        for unit, codes in units:
            for group in params.request_groups():
                key = params.partition_key(unit, group)
                if full or key not in watermark.partitions or unit in recent:
                    requests.append(
                        ExtractionRequest(
                            partition_key=key,
                            url=self._values_url(
                                params,
                                group.levels or params.territorial_levels,
                                ",".join(group.variables),
                                ",".join(codes),
                                group.classifications,
                            ),
                            artifact_name=f"t{params.table}-{key}.json",
                            reference_period=unit,
                            max_bytes=params.max_bytes,
                        )
                    )
                else:
                    skipped.append(key)
        notes = [f"períodos disponíveis: {len(periods)}"]
        if skipped:
            notes.append(f"partições já ingeridas e fora da janela de revisão: {skipped}")
        return ExtractionPlan(
            dataset_id=dataset_id,
            requests=tuple(requests),
            notes=tuple(notes),
            metadata={"available_periods": periods, "refresh_recent_periods": sorted(recent)},
        )

    def validate_raw(  # noqa: PLR0911, PLR0912, PLR0915 - verificações sequenciais e independentes
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
        group = params.request_group(request.partition_key)
        expected_levels = (
            frozenset(lv[1:] for lv in group.levels) if group.levels else params.level_codes
        )
        if set(levels) != expected_levels:
            errors.append(
                f"níveis territoriais {dict(levels)} diferem dos esperados "
                f"{sorted(expected_levels)}"
            )
        period_key = f"{params.period_dimension}C"
        periods = Counter(r[period_key] for r in rows)
        if params.group_periods_by_year:
            # Meses ou trimestres do ano da partição, no formato do tipo declarado.
            unexpected = {
                p: n
                for p, n in periods.items()
                if not params.period_valid(p) or p[:4] != request.reference_period
            }
            if unexpected:
                errors.append(f"períodos inesperados: {unexpected}")
        elif set(periods) != {request.reference_period}:
            errors.append(f"períodos inesperados: {dict(periods)}")
        var_key = f"{params.variable_dimension}C"
        variables = set(Counter(r[var_key] for r in rows))
        expected_vars = group.variables
        if variables != set(expected_vars):
            errors.append(
                f"variáveis {sorted(variables)} diferem das esperadas {list(expected_vars)}"
            )

        dim_keys = sorted(k for k in keys if re.fullmatch(r"D\d+C", k))
        # O nível (NC) faz parte da identidade: códigos se repetem entre níveis (Brasil=Norte=1).
        identities = Counter((r["NC"], *(r[k] for k in dim_keys)) for r in rows)
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
            "territories": len({(r["NC"], r[f"{params.territory_dimension}C"]) for r in rows}),
            "levels": dict(sorted(levels.items())),
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
        url = self._values_url(params, ("n1",), params.variables[0], "last")
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
