"""Panorama do Brasil: taxonomia do portal e KPIs do Tier 1 (ADR-0010).

``configs/catalog/panorama.toml`` define os grandes temas, os subtemas e, em
cada subtema, os KPIs de panorama. Cada KPI vem de uma tabela do acervo SIDRA
(a de menor detalhe da família) e lista os filtros oferecidos.

Um item está publicado quando o portal (``configs/portal/<escopo>.toml`` e
os fragmentos em ``configs/portal/<escopo>/``) tem o KPI indicado em ``kpi``
ou, sem ``kpi``, um KPI com o mesmo ``id`` do item (KPIs gerados por
``odb panorama gerar``). Os demais são planejados: aparecem na navegação como
"em preparação" e ainda não têm dados na Gold.

``variavel`` fixa a variável SIDRA do KPI quando a regra automática do gerador
(primeira variável que não é coeficiente de variação, intervalo de confiança
ou distribuição percentual) não serve. ``requer_categoria`` marca os KPIs cujo
Total é só o universo da tabela (por exemplo, "Municípios com Plano Diretor"
daria o número de municípios): eles esperam os códigos das classificações.

As validações aqui são estruturais: unicidade, filtros declarados e, quando o
snapshot do acervo é informado, a existência de cada tabela e o SHA-256 do
snapshot. Os metadados das tabelas (variáveis, períodos, níveis) são
verificados na fonte por ``odb panorama verificar``.
"""

from __future__ import annotations

import csv
import hashlib
import tomllib
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

PANORAMA_ID = r"^[a-z][a-z0-9_]{0,63}$"
SIDRA_TABLE = r"^[1-9][0-9]{0,5}$"


class PanoramaConfigError(ValueError):
    """Panorama inválido ou incoerente com o acervo ou com o portal."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PanoramaFilter(_Strict):
    """Filtro (dimensão de recorte) oferecido por um ou mais temas."""

    id: str = Field(pattern=PANORAMA_ID)
    label: str = Field(min_length=1)


class PanoramaKpi(_Strict):
    """KPI de panorama: o Total de uma tabela do acervo, com seus filtros."""

    id: str = Field(pattern=PANORAMA_ID)
    label: str = Field(min_length=1)
    tabela: str = Field(pattern=SIDRA_TABLE)
    pesquisa: str = Field(min_length=1)
    filtros: tuple[str, ...] = ()
    kpi: str | None = Field(default=None, pattern=PANORAMA_ID)
    nota: str | None = None
    variavel: str | None = Field(default=None, pattern=r"^\d{1,8}$")
    requer_categoria: bool = False
    # Em espera (por exemplo, timeout persistente na fonte): fora da geração, com o motivo.
    pausado: str | None = Field(default=None, min_length=1)
    # Dimensão principal (onda Total + %), quando a proposta automática não serve.
    dimensao: str | None = Field(default=None, pattern=r"^c\d{1,6}$")
    # Primeiro período mostrado no portal (a série completa fica na Silver).
    periodo_inicial: str | None = Field(default=None, pattern=r"^\d{4,6}$")


class PanoramaSubtheme(_Strict):
    """Subtema."""

    id: str = Field(pattern=PANORAMA_ID)
    label: str = Field(min_length=1)
    kpis: tuple[PanoramaKpi, ...] = Field(min_length=1)


class PanoramaTheme(_Strict):
    """Grande tema, com os filtros que fazem sentido na sua hierarquia."""

    id: str = Field(pattern=PANORAMA_ID)
    label: str = Field(min_length=1)
    filtros: tuple[str, ...] = ()
    subtemas: tuple[PanoramaSubtheme, ...] = Field(min_length=1)


class Panorama(_Strict):
    """Taxonomia completa do portal."""

    config_version: str
    acervo: str
    acervo_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acervo_obtido_em: str
    acervo_origem: str
    filtros: tuple[PanoramaFilter, ...] = Field(min_length=1)
    temas: tuple[PanoramaTheme, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _structure(self) -> Panorama:
        problems: list[str] = []
        known = [f.id for f in self.filtros]
        problems += _repeated("filtro", known)
        problems += _repeated("tema", [t.id for t in self.temas])
        problems += _repeated("subtema", [s.id for _, s in self.subthemes()])
        problems += _repeated("KPI", [k.id for _, _, k in self.items()])
        problems += _repeated("kpi do portal", [k.kpi for _, _, k in self.items() if k.kpi])
        for theme in self.temas:
            unknown = sorted(set(theme.filtros) - set(known))
            if unknown:
                problems.append(f"tema {theme.id}: filtros não declarados {unknown}")
            for sub in theme.subtemas:
                for kpi in sub.kpis:
                    outside = [f for f in kpi.filtros if f not in theme.filtros]
                    if outside:
                        problems.append(f"{kpi.id}: filtros fora do tema {theme.id}: {outside}")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def subthemes(self) -> list[tuple[PanoramaTheme, PanoramaSubtheme]]:
        """Pares (tema, subtema), na ordem do arquivo."""
        return [(t, s) for t in self.temas for s in t.subtemas]

    def items(self) -> list[tuple[PanoramaTheme, PanoramaSubtheme, PanoramaKpi]]:
        """Triplas (tema, subtema, KPI), na ordem do arquivo."""
        return [(t, s, k) for t in self.temas for s in t.subtemas for k in s.kpis]

    def filter_label(self, filter_id: str) -> str:
        """Rótulo de um filtro declarado."""
        return next(f.label for f in self.filtros if f.id == filter_id)

    def tables(self) -> list[str]:
        """Códigos SIDRA referenciados, sem repetição, na ordem do arquivo."""
        return list(dict.fromkeys(k.tabela for _, _, k in self.items()))


def _repeated(kind: str, ids: Iterable[str]) -> list[str]:
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    return [f"{kind} repetido: {dup}"] if dup else []


def load_panorama(path: str | Path) -> Panorama:
    """Carrega e valida a estrutura de ``panorama.toml``."""
    path = Path(path)
    try:
        return Panorama.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"{path}: panorama inválido: {exc}"
        raise PanoramaConfigError(msg) from exc


def read_acervo(path: str | Path) -> tuple[dict[str, str], str]:
    """Snapshot do acervo (``id;nome``, sem cabeçalho) e seu SHA-256.

    É a exportação oficial "Salvar TSV" do acervo do SIDRA, em UTF-8 com BOM.
    """
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    tables: dict[str, str] = {}
    for row in csv.reader(raw.decode("utf-8-sig").splitlines(), delimiter=";"):
        if len(row) >= 2 and row[0].strip().isdigit():  # noqa: PLR2004 - id;nome
            tables[row[0].strip()] = row[1].strip()
    return tables, digest


def check_against_acervo(panorama: Panorama, acervo_path: str | Path) -> dict[str, str]:
    """Confere o SHA-256 do snapshot e a existência de cada tabela.

    Devolve código → título oficial das tabelas do panorama.
    """
    tables, digest = read_acervo(acervo_path)
    problems: list[str] = []
    if digest != panorama.acervo_sha256:
        problems.append(f"SHA-256 do acervo {digest} difere do registrado {panorama.acervo_sha256}")
    missing = [t for t in panorama.tables() if t not in tables]
    if missing:
        problems.append(f"tabelas ausentes do acervo: {missing}")
    if problems:
        raise PanoramaConfigError("; ".join(problems))
    return {t: tables[t] for t in panorama.tables()}


def resolve_links(panorama: Panorama, portal_kpis: Iterable[str]) -> dict[str, str | None]:
    """KPI do portal de cada item: ``kpi`` explícito ou o próprio ``id``; ``None`` se planejado."""
    portal = set(portal_kpis)
    return {
        k.id: k.kpi if k.kpi is not None else (k.id if k.id in portal else None)
        for _, _, k in panorama.items()
    }


def check_against_portal(panorama: Panorama, portal_kpis: Mapping[str, object]) -> None:
    """Cada KPI do portal aparece em exatamente um item do panorama, e vice-versa."""
    links = resolve_links(panorama, portal_kpis)
    explicit = {k.kpi for _, _, k in panorama.items() if k.kpi}
    linked = [v for v in links.values() if v is not None]
    problems: list[str] = []
    unknown = sorted(explicit - set(portal_kpis))
    if unknown:
        problems.append(f"panorama aponta para KPIs inexistentes no portal: {unknown}")
    problems += _repeated("KPI do portal ligado a mais de um item", linked)
    orphan = sorted(set(portal_kpis) - set(linked))
    if orphan:
        problems.append(f"KPIs do portal fora do panorama: {orphan}")
    if problems:
        raise PanoramaConfigError("; ".join(problems))
