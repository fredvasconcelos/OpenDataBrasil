"""Confere isolamento, retomada e interrupção da cadeia por manifesto."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).parents[3] / "infrastructure/scripts/carga_lote_sequencial.py"
SPEC = importlib.util.spec_from_file_location("carga_lote", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifesto.json"
    path.write_text(
        json.dumps(
            {
                "lote": "n1-teste",
                "imagem_tag": "teste",
                "imagem_id": "sha256:teste",
                "medidas": [{"dataset": "ibge-medida-t5932-v6564"}],
                "arquivos_sha256": {},
            }
        )
    )
    return path


def test_etapas_sequenciais_usam_so_o_lote_e_nunca_ativam(manifest: Path, tmp_path: Path) -> None:
    batch = MODULE.Batch(manifest, tmp_path)
    calls = []

    def run(command: list[str], **kwargs: Any) -> CompletedProcess[str]:
        calls.append(command)
        if command[1:3] == ["image", "inspect"]:
            return CompletedProcess(command, 0, stdout="sha256:teste\n")
        if command[-3:] == ["odb", "gold", "build"]:
            kwargs["stdout"].write(
                json.dumps(
                    {
                        "status": "succeeded",
                        "release": {"release_id": "candidata"},
                    },
                    indent=2,
                )
                + "\n"
            )
        return CompletedProcess(command, 0)

    with patch.object(MODULE.subprocess, "run", run):
        batch.run()
    assert list(batch.state["etapas"]) == [
        "captura_ibge-medida-t5932-v6564",
        "silver",
        "gold",
        "release_check",
        "backup",
    ]
    assert calls[1][-4:] == ["odb", "ingest", "run", "ibge-medida-t5932-v6564"]
    assert calls[2][-4:] == ["odb", "silver", "build", "ibge-medida-t5932-v6564"]
    assert all("activate" not in command for command in calls)
    assert batch.state["fase"] == "aguardando_conferencia_final"
    with patch.object(
        MODULE.subprocess, "run", return_value=CompletedProcess([], 0, stdout="sha256:teste\n")
    ) as runner:
        MODULE.Batch(manifest, tmp_path).run()
    assert runner.call_count == 1  # Apenas confere a imagem; recibos evitam repetir etapas.


def test_falha_de_captura_impede_silver_e_gold(manifest: Path, tmp_path: Path) -> None:
    batch = MODULE.Batch(manifest, tmp_path)
    with (
        patch.object(
            MODULE.subprocess,
            "run",
            side_effect=[
                CompletedProcess([], 0, stdout="sha256:teste\n"),
                CompletedProcess([], 1),
            ],
        ),
        pytest.raises(RuntimeError, match="captura_ibge-medida-t5932-v6564 falhou"),
    ):
        batch.run()
    assert set(batch.state["etapas"]) == {"captura_ibge-medida-t5932-v6564"}
    assert batch.state["etapas"]["captura_ibge-medida-t5932-v6564"]["codigo"] == 1
    assert not (tmp_path / "silver.log").exists()


def test_imagem_diferente_impede_qualquer_captura(manifest: Path, tmp_path: Path) -> None:
    batch = MODULE.Batch(manifest, tmp_path)
    with (
        patch.object(
            MODULE.subprocess, "run", return_value=CompletedProcess([], 0, stdout="sha256:outra\n")
        ),
        pytest.raises(ValueError, match="Imagem local difere"),
    ):
        batch.run()
    assert not batch.state["etapas"]


def test_manifesto_e_arquivos_alterados_nao_reutilizam_recibos(
    manifest: Path, tmp_path: Path
) -> None:
    batch = MODULE.Batch(manifest, tmp_path)
    batch.update()
    data = json.loads(manifest.read_text())
    data["medidas"].append({"dataset": "outro-dataset"})
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Manifesto mudou"):
        MODULE.Batch(manifest, tmp_path)
    data["arquivos_sha256"] = {str(manifest): "outro-hash"}
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Arquivo mudou"):
        MODULE.Batch(manifest, tmp_path / "outro-destino")
