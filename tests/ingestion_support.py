"""Apoio aos testes de ingestão: fontes simuladas e registro em memória."""

import io
import json
import re
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

import httpx

from odb_ingestion import ArtifactRecord, DuplicateContentError, SourceCatalog, StoredArtifact
from odb_ingestion.contract import PartitionState, Watermark

FIXTURES = Path(__file__).parent / "fixtures"
SIDRA_FIXTURES = FIXTURES / "ibge" / "sidra"
TEST_SOURCES = FIXTURES / "sources"
DTB_URL_PATH = (
    "/organizacao_do_territorio/estrutura_territorial/divisao_territorial/2025/DTB_2025.zip"
)
DTB_MEMBERS = [
    "DISTRITOS-SUBDISTRITOS_NOVOS_E_EXTINTOS_2025.ods",
    "RELATORIO_DTB_BRASIL_2025_DISTRITOS.ods",
    "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods",
    "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.xls",
]
_VALUES = re.compile(r"^/values/t/(\d+)/(n\d+)/all/v/([\d,]+|all)/p/(\w+)$")


def fixture_bytes(name: str) -> bytes:
    return (SIDRA_FIXTURES / name).read_bytes()


def synthetic_period(period: str) -> bytes:
    """Resposta SINTÉTICA: fixture real de 2025 com o período trocado."""
    payload = json.loads(fixture_bytes("t6579_n3_p2025.json"))
    for row in payload[1:]:
        row["D3C"] = row["D3N"] = period
    return json.dumps(payload, ensure_ascii=False).encode()


def make_dtb_zip(members: list[str] | None = None) -> bytes:
    """ZIP SINTÉTICO com os nomes de membros do DTB_2025.zip real."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in members if members is not None else DTB_MEMBERS:
            archive.writestr(name, f"conteúdo fictício de {name}\n" * 20)
    return buffer.getvalue()


@dataclass
class FakeSources:
    """Servidor simulado do SIDRA e do geoftp, com injeção de falhas por caminho."""

    overrides: dict[str, Callable[[httpx.Request], httpx.Response]] = field(default_factory=dict)
    dtb_zip: bytes = field(default_factory=make_dtb_zip)
    dtb_etag: str = '"dtb-v1"'
    requests: list[httpx.Request] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:  # noqa: PLR0911 - roteador
        self.requests.append(request)
        path = request.url.path
        if path in self.overrides:
            return self.overrides[path](request)
        if request.url.host == "geoftp.ibge.gov.br":
            if path == DTB_URL_PATH:
                if request.headers.get("if-none-match") == self.dtb_etag:
                    return httpx.Response(304, headers={"etag": self.dtb_etag})
                return httpx.Response(
                    200,
                    content=self.dtb_zip,
                    headers={
                        "content-type": "application/zip",
                        "etag": self.dtb_etag,
                        "last-modified": "Thu, 26 Mar 2026 21:07:36 GMT",
                    },
                )
            return httpx.Response(200, content=b"<html>index</html>")
        match = _VALUES.match(path)
        if not match:
            return httpx.Response(404, content=b"not found")
        table, level, _vars, period = match.groups()
        json_headers = {"content-type": "application/json; charset=utf-8"}
        if table == "999999":
            return httpx.Response(400, content=fixture_bytes("error_table_not_found.txt"))
        if level == "n1" and period in ("all", "last"):
            return httpx.Response(
                200, content=fixture_bytes(f"t{table}_n1_periods.json"), headers=json_headers
            )
        name = f"t{table}_{level}_p{period}.json"
        if (SIDRA_FIXTURES / name).exists():
            return httpx.Response(200, content=fixture_bytes(name), headers=json_headers)
        if table == "6579":
            return httpx.Response(200, content=synthetic_period(period), headers=json_headers)
        return httpx.Response(404, content=b"sem fixture")

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


class InMemoryRegistry:
    """Implementação em memória de ``IngestionRegistry`` para testes unitários."""

    def __init__(self) -> None:
        self.synced: list[SourceCatalog] = []
        self.ingestions: dict[str, dict[str, Any]] = {}
        self.artifacts: list[ArtifactRecord] = []
        self.watermarks: dict[str, dict[str, PartitionState]] = {}
        self.fail_next_store_with_duplicate = False

    def sync_catalog(self, catalog: SourceCatalog) -> None:
        self.synced.append(catalog)

    def start_ingestion(
        self, ingestion_id: str, dataset_id: str, run_id: str | None, parameters: Mapping[str, Any]
    ) -> None:
        self.ingestions[ingestion_id] = {"dataset_id": dataset_id, "status": "running"}

    def save_plan(self, ingestion_id: str, plan: Mapping[str, Any]) -> None:
        self.ingestions[ingestion_id]["plan"] = plan

    def find_stored(self, checksum_sha256: str) -> StoredArtifact | None:
        for a in self.artifacts:
            if a.status == "stored" and a.checksum_sha256 == checksum_sha256:
                assert a.storage_uri is not None
                return StoredArtifact(a.artifact_id, a.storage_uri)
        return None

    def record_artifact(self, record: ArtifactRecord) -> None:
        if record.status == "stored" and self.fail_next_store_with_duplicate:
            self.fail_next_store_with_duplicate = False
            # Simula outro processo gravando o mesmo conteúdo antes deste.
            self.artifacts.append(
                replace(record, artifact_id="concurrent", storage_uri="file:///lakehouse/other")
            )
            raise DuplicateContentError("simulado")
        self.artifacts.append(record)

    def get_watermark(self, dataset_id: str) -> Watermark:
        return Watermark(partitions=dict(self.watermarks.get(dataset_id, {})))

    def update_watermark(
        self, dataset_id: str, partitions: Mapping[str, tuple[PartitionState, str | None]]
    ) -> None:
        self.watermarks.setdefault(dataset_id, {}).update({k: v[0] for k, v in partitions.items()})

    def finish_ingestion(
        self,
        ingestion_id: str,
        status: Literal["succeeded", "failed"],
        stats: Mapping[str, Any],
        error: str | None,
    ) -> None:
        self.ingestions[ingestion_id].update(status=status, stats=stats, error=error)

    def by_status(self, status: str) -> list[ArtifactRecord]:
        return [a for a in self.artifacts if a.status == status]
