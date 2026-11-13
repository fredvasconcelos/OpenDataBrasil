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
from typing import Literal

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
    # Categoria de referência das classificações sem Total (cNNN → código da categoria):
    # o KPI mostra essa categoria (ex.: rebanho bovino), já que as demais não se somam.
    referencia: dict[str, str] = Field(default_factory=dict)
    # Categoria cuja participação no Total colore o mapa (KPIs de categoria).
    categoria_mapa: str | None = Field(default=None, pattern=r"^\d+$")
    # Agregação no tempo (ADR-0017) para KPIs mensais e trimestrais: "soma" (fluxos),
    # "media" (números-índice, médias por período) ou "ultimo" (acumulados em 12
    # meses, estimativas revisadas). Sem o campo, só o grão publicado.
    agregacao_tempo: Literal["soma", "media", "ultimo", "composicao"] | None = None
    # Tabelas-irmãs (ADR-0018): a mesma variável com uma classificação a mais (cor ou
    # raça, idade, instrução...), que entra como detalhe do KPI.
    complementos: tuple[str, ...] = Field(default=(), max_length=12)
    # Correção de valores em moeda (ADR-0020): "ipca" põe o "Corrigir por: IPCA geral",
    # com o índice do próprio período (mês, ou média dos meses do trimestre ou do ano).
    # Só para valores nominais: rendimentos já deflacionados pela fonte ficam de fora.
    correcao: Literal["ipca"] | None = None


class PanoramaExternal(_Strict):
    """KPI curado de outra fonte (fora do SIDRA) no mesmo subtema (ex.: Sinesp, ADR-0012).

    Não passa pelo gerador nem pela conferência no acervo do SIDRA: o KPI e o indicador
    são curados à mão. Só a ligação com o portal é conferida.
    """

    id: str = Field(pattern=PANORAMA_ID)
    label: str = Field(min_length=1)
    fonte: str = Field(min_length=1)  # dataset ou série de origem (configs/sources)
    tabela: str = Field(min_length=1)  # identificador da tabela na fonte
    kpi: str = Field(pattern=PANORAMA_ID)


class PanoramaSubtheme(_Strict):
    """Subtema."""

    id: str = Field(pattern=PANORAMA_ID)
    label: str = Field(min_length=1)
    kpis: tuple[PanoramaKpi, ...] = Field(min_length=1)
    externos: tuple[PanoramaExternal, ...] = ()


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
    external = [e.kpi for t in panorama.temas for s in t.subtemas for e in s.externos]
    explicit = {k.kpi for _, _, k in panorama.items() if k.kpi} | set(external)
    linked = [v for v in links.values() if v is not None] + external
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
