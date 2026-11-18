"""Confere o guarda, incluindo divergências entre o índice e os arquivos locais."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "infrastructure/scripts/public_boundary.py"
SPEC = importlib.util.spec_from_file_location("public_boundary", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)


@pytest.mark.parametrize(
    "name",
    [
        "docs/relatorios/relato.md",
        "docs-local/acesso.md",
        "design-system/portal/app.tsx",
        "design-system/reference/tela.png",
        "AGENTS.md",
        "copia.dump",
        ".env",
        "configs/evidencias-amostra.json",
        "docs/architecture/plano-desempenho-portal.md",
    ],
)
def test_guarda_recusa_caminhos_internos(name: str) -> None:
    assert BOUNDARY.path_problems(name, "100644")


def test_guarda_aceita_exemplos_e_ativos_publicos() -> None:
    for name in [
        ".env.example",
        "infrastructure/vitrine/.env.example",
        "apps/api/app.py",
        "design-system/assets/marca.svg",
        "CLAUDE.md",
        "NOTICE",
    ]:
        assert not BOUNDARY.path_problems(name, "100644")
    assert BOUNDARY.path_problems("marca.svg", "120000")
    assert BOUNDARY.path_problems("../arquivo", "100644")


def test_guarda_aponta_regra_sem_revelar_o_conteudo() -> None:
    address = ".".join(["192", "168", "10", "20"])
    data = f"texto\nhttp://{address}\n".encode()
    problems = BOUNDARY.content_problems(data)
    assert len(problems) == 1
    assert "linha 2" in problems[0]
    assert address not in problems[0]


def _git(root: Path, *args: str) -> None:
    BOUNDARY.git(root, *args)


@pytest.mark.skipif(
    shutil.which("git") is None, reason="Integração com Git conferida no host e no CI"
)
def test_guarda_le_o_indice_e_ignora_configuracao_local(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    address = ".".join(["192", "168", "10", "20"])
    source = tmp_path / "app.py"
    source.write_text(f"# http://{address}\n")
    _git(tmp_path, "add", "app.py")
    source.write_text("# arquivo local já corrigido\n")
    (tmp_path / ".env").write_text("CONFIGURACAO_LOCAL=nao_incluir\n")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    count, problems = BOUNDARY.snapshot_index(tmp_path, snapshot)
    assert count == 1
    assert problems
    assert not (snapshot / ".env").exists()
    assert address in (snapshot / "app.py").read_text()


@pytest.mark.skipif(
    shutil.which("git") is None, reason="Integração com Git conferida no host e no CI"
)
def test_guarda_nao_segue_links_simbolicos_no_indice(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    external = tmp_path / "local.env"
    external.write_text("CONFIGURACAO_LOCAL=nao_ler\n")
    (tmp_path / "app.py").symlink_to(external)
    _git(tmp_path, "add", "app.py")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    _, problems = BOUNDARY.snapshot_index(tmp_path, snapshot)
    assert any("link simbólico" in problem for problem in problems)
    assert not (snapshot / "app.py").exists()
