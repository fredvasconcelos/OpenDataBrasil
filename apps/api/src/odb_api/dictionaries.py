"""Dicionários documentais versionados, sem confundir snapshot com publicação."""

from __future__ import annotations

import csv
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from odb_api.gold import NotFoundError


class DictionaryEntryOut(BaseModel):
    """Ficha, referências e códigos obtidos; lacunas permanecem explícitas."""

    entry_id: str
    indicator_id: str
    version: str
    documentary_status: str = "revisao_parcial"
    document: dict[str, Any]
    links: list[dict[str, Any]] = Field(default_factory=list)
    methods: list[dict[str, Any]] = Field(default_factory=list)
    fields: list[dict[str, str]] = Field(default_factory=list)
    codes: list[dict[str, str]] = Field(default_factory=list)
    context: dict[str, Any] | None = None
    expansion: dict[str, str] | None = None
    preparation: dict[str, Any] | None = None


class DictionaryIndexOut(BaseModel):
    """Inventário documental, incluindo apoios e candidatas sem ativação."""

    version: str
    status: str = "documentacao_parcial_nao_certifica_disponibilidade"
    entries: list[dict[str, str | None]]
    expansions: list[dict[str, str]]
    artifacts: dict[str, str]
    preparation: dict[str, Any] | None = None


class DictionaryCatalog:
    """Lê somente os arquivos conhecidos do acervo documental distribuído."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        names = (
            "fichas.json",
            "metodos.json",
            "ligacoes.json",
            "campos.csv",
            "codigos.csv",
            "contextos-complementares.json",
            "candidatas.csv",
        )
        self.artifacts = {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names
        }
        self.version = hashlib.sha256(
            json.dumps(self.artifacts, sort_keys=True).encode()
        ).hexdigest()
        self.documents = {item["ficha"]: item for item in self._json("fichas.json")}
        self.methods = {item["id"]: item for item in self._json("metodos.json")}
        self.links = self._json("ligacoes.json")
        self.fields = self._csv("campos.csv")
        self.codes = self._csv("codigos.csv")
        self.contexts = self._json("contextos-complementares.json")["fichas"]
        self.expansions = {item["kpi"]: item for item in self._csv("candidatas.csv")}
        preparation = directory / "preparacao-expansao.json"
        self.preparation = self._json(preparation.name) if preparation.is_file() else None

    def _json(self, name: str) -> Any:
        return json.loads((self.directory / name).read_text(encoding="utf-8"))

    def _csv(self, name: str) -> list[dict[str, str]]:
        with (self.directory / name).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def index(self) -> DictionaryIndexOut:
        """Lista a documentação, sem promover candidatas à navegação publicada."""
        return DictionaryIndexOut(
            version=self.version,
            entries=[
                {
                    "entry_id": key,
                    "indicator_id": doc["indicator_id"],
                    "kpi_id": doc["kpi_id"],
                    "label": doc["nome_portal"],
                    "snapshot_status": doc["status"],
                }
                for key, doc in self.documents.items()
            ],
            expansions=list(self.expansions.values()),
            artifacts=self.artifacts,
            preparation=self.preparation,
        )

    def entry(self, entry_id: str) -> DictionaryEntryOut:
        """Vincula por ficha, tabela e variável; não resolve códigos por nome."""
        doc = self.documents.get(entry_id)
        if doc is None:
            raise NotFoundError(f"dicionário não encontrado: {entry_id}")
        links = [item for item in self.links if item["ficha"] == entry_id]
        pairs = {(str(item["tabela"]), str(item["variavel"])) for item in links}
        tables = {table for table, _ in pairs}
        return DictionaryEntryOut(
            entry_id=entry_id,
            indicator_id=doc["indicator_id"],
            version=self.version,
            document=doc,
            links=links,
            methods=[self.methods[key] for key in doc["metodos"]],
            fields=[item for item in self.fields if (item["tabela"], item["variavel"]) in pairs],
            codes=[item for item in self.codes if item["tabela"] in tables],
            context=self.contexts.get(entry_id),
            expansion=self.expansions.get(entry_id),
            preparation=next(
                (
                    item
                    for item in (self.preparation or {}).get("indicadores", [])
                    if item["kpi"] == entry_id
                ),
                None,
            ),
        )


@lru_cache(maxsize=4)
def load_dictionaries(directory: str) -> DictionaryCatalog:
    """Uma leitura por diretório na imagem imutável; reinício carrega nova versão."""
    return DictionaryCatalog(Path(directory))
