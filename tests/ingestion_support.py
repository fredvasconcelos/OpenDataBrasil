"""Apoio aos testes de ingestão: fontes simuladas e registro em memória."""

import io
import json
import re
import zipfile
from collections.abc import Callable, Mapping, Sequence
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
DTB_FIXTURES = FIXTURES / "ibge" / "dtb"
MESH_BASE = (
    "/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/"
)
# Códigos reais de UF (DTB) com a Grande Região pelo 1º dígito.
UF_CODES = [
    ("11", "Rondônia", "RO"), ("12", "Acre", "AC"), ("13", "Amazonas", "AM"),
    ("14", "Roraima", "RR"), ("15", "Pará", "PA"), ("16", "Amapá", "AP"),
    ("17", "Tocantins", "TO"), ("21", "Maranhão", "MA"), ("22", "Piauí", "PI"),
    ("23", "Ceará", "CE"), ("24", "Rio Grande do Norte", "RN"), ("25", "Paraíba", "PB"),
    ("26", "Pernambuco", "PE"), ("27", "Alagoas", "AL"), ("28", "Sergipe", "SE"),
    ("29", "Bahia", "BA"), ("31", "Minas Gerais", "MG"), ("32", "Espírito Santo", "ES"),
    ("33", "Rio de Janeiro", "RJ"), ("35", "São Paulo", "SP"), ("41", "Paraná", "PR"),
    ("42", "Santa Catarina", "SC"), ("43", "Rio Grande do Sul", "RS"),
    ("50", "Mato Grosso do Sul", "MS"), ("51", "Mato Grosso", "MT"), ("52", "Goiás", "GO"),
    ("53", "Distrito Federal", "DF"),
]  # fmt: skip
# Municípios reais (DTB 2025) e as duas lagoas da malha municipal real, que não são municípios.
MESH_MUNICIPALITIES = [
    ("1100015", "Alta Floresta D'Oeste", "RO"),
    ("2927408", "Salvador", "BA"),
    ("5103403", "Cuiabá", "MT"),
    ("4300001", "Lagoa Mirim", "RS"),
    ("4300002", "Lagoa dos Patos", "RS"),
]
_VALUES = re.compile(
    r"^/values/t/(\d+)/((?:n\d+/all/?)+)/v/([\d,]+|all)/p/(\w+)((?:/c\d+/[\d,a-z]+)*)$"
)


def fixture_bytes(name: str) -> bytes:
    return (SIDRA_FIXTURES / name).read_bytes()


def synthetic_period(period: str) -> bytes:
    """Resposta SINTÉTICA: fixture real de 2025 com o período trocado."""
    payload = json.loads(fixture_bytes("t6579_n1n2n3_p2025.json"))
    for row in payload[1:]:
        row["D3C"] = row["D3N"] = period
    return json.dumps(payload, ensure_ascii=False).encode()


def make_mesh_zip(member: str, fields: list[str], records: Sequence[tuple[str, ...]]) -> bytes:
    """Malha SINTÉTICA no formato da Malha Municipal 2022 (shapefile em ZIP).

    Nomes de membros, campos do DBF e ``.prj`` (SIRGAS 2000) seguem o arquivo
    real. As geometrias são quadrados de 1° numa grade, vizinhos entre si, e
    não representam os territórios.
    """
    import shapefile  # noqa: PLC0415 - só os testes de malha precisam

    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    with shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON) as writer:
        for name in fields:
            writer.field(name, "C", size=60)
        writer.field("AREA_KM2", "N", size=12, decimal=3)
        for i, record in enumerate(records):
            x, y = -60 + i % 6, -10 - i // 6
            writer.poly([[[x, y], [x, y + 1], [x + 1, y + 1], [x + 1, y], [x, y]]])
            writer.record(*record, 12345.678)
    prj = (
        'GEOGCS["GCS_SIRGAS_2000",DATUM["D_SIRGAS_2000",SPHEROID["GRS_1980",6378137.0,'
        '298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{member}.shp", shp.getvalue())
        archive.writestr(f"{member}.shx", shx.getvalue())
        archive.writestr(f"{member}.dbf", dbf.getvalue())
        archive.writestr(f"{member}.prj", prj)
        archive.writestr(f"{member}.cpg", "UTF-8")
    return buffer.getvalue()


def make_meshes() -> dict[str, bytes]:
    """Malhas sintéticas de UF e de municípios, por caminho no geoftp."""
    return {
        MESH_BASE + "BR_UF_2022.zip": make_mesh_zip(
            "BR_UF_2022",
            ["CD_UF", "NM_UF", "SIGLA_UF", "NM_REGIAO"],
            [(c, n, s, "") for c, n, s in UF_CODES],
        ),
        MESH_BASE + "BR_Municipios_2022.zip": make_mesh_zip(
            "BR_Municipios_2022", ["CD_MUN", "NM_MUN", "SIGLA_UF"], MESH_MUNICIPALITIES
        ),
    }


def make_dtb_zip(members: list[str] | None = None) -> bytes:
    """ZIP com os nomes de membros do DTB_2025.zip real.

    A planilha de municípios (ODS) é o arquivo REAL da DTB 2025. Os demais
    membros têm conteúdo fictício.
    """
    real = {
        "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods": (
            DTB_FIXTURES / "RELATORIO_DTB_BRASIL_2025_MUNICIPIOS.ods"
        ).read_bytes()
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in members if members is not None else DTB_MEMBERS:
            archive.writestr(name, real.get(name, f"conteúdo fictício de {name}\n".encode() * 20))
    return buffer.getvalue()


@dataclass
class FakeSources:
    """Servidor simulado do SIDRA e do geoftp, com injeção de falhas por caminho."""

    overrides: dict[str, Callable[[httpx.Request], httpx.Response]] = field(default_factory=dict)
    dtb_zip: bytes = field(default_factory=make_dtb_zip)
    dtb_etag: str = '"dtb-v1"'
    meshes: dict[str, bytes] = field(default_factory=make_meshes)
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
            if path in self.meshes:
                return httpx.Response(
                    200, content=self.meshes[path], headers={"content-type": "application/zip"}
                )
            return httpx.Response(200, content=b"<html>index</html>")
        match = _VALUES.match(path)
        if not match:
            return httpx.Response(404, content=b"not found")
        table, levels, variables, period, classifications = match.groups()
        level = "".join(part for part in levels.split("/") if part.startswith("n"))
        json_headers = {"content-type": "application/json; charset=utf-8"}
        if table == "999999":
            return httpx.Response(400, content=fixture_bytes("error_table_not_found.txt"))
        if level == "n1" and period in ("all", "last"):
            return httpx.Response(
                200, content=fixture_bytes(f"t{table}_n1_periods.json"), headers=json_headers
            )
        name = f"t{table}_{level}_p{period}.json"
        # Classificações com categorias listadas entram no nome (divisão por categoria).
        parts = classifications.strip("/").split("/") if classifications else []
        listed = "".join(
            f"_{cid}-{cats}"
            for cid, cats in zip(parts[::2], parts[1::2], strict=True)
            if cats != "all" and "," not in cats
        )
        by_variable = f"t{table}_{level}_p{period}_v{variables}{listed}.json"
        if (SIDRA_FIXTURES / by_variable).exists():
            return httpx.Response(200, content=fixture_bytes(by_variable), headers=json_headers)
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
        self.watermark_artifacts: dict[str, dict[str, str]] = {}
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
        self.watermark_artifacts.setdefault(dataset_id, {}).update(
            {k: v[1] for k, v in partitions.items() if v[1] is not None}
        )

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
