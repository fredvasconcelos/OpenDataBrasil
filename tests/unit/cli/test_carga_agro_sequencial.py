"""A cadeia funciona sem agente e aguarda as checagens antes de publicar dados."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).parents[3] / "infrastructure/scripts/carga_agro_sequencial.py"
SPEC = importlib.util.spec_from_file_location("carga_agro", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_gold_so_comeca_apos_captura_e_silver_sem_ativar_release(tmp_path: Path) -> None:
    chain = MODULE.Chain(tmp_path)
    commands: list[list[str]] = []

    def container(stage: str, command: list[str], mounts: list[str] | None = None) -> None:
        if stage == "gold":
            assert chain.done("captura")
            assert chain.done("silver")
            (tmp_path / "gold.log").write_text(
                json.dumps(
                    {
                        "status": "succeeded",
                        "rows": {"indicator_observation": 123},
                        "release": {"release_id": "candidato"},
                    },
                    indent=2,
                )
                + "\n"
            )
        chain.receipt(stage, 0)

    def command(stage: str, args: list[str]) -> None:
        commands.append(args)
        assert chain.done("gold")
        chain.receipt(stage, 0)

    with patch.object(chain, "container", container), patch.object(chain, "command", command):
        chain.run()
    assert chain.state["fase"] == "aguardando_conferencia_final"
    assert chain.state["release_candidato"] == "candidato"
    assert len(commands) == 2
    assert all("activate" not in args for args in commands)


def test_recibo_de_sucesso_evita_repetir_etapa_ao_retomar(tmp_path: Path) -> None:
    chain = MODULE.Chain(tmp_path)
    chain.receipt("captura", 0)
    resumed = MODULE.Chain(tmp_path)
    with patch.object(MODULE.subprocess, "run", side_effect=AssertionError("Docker não esperado")):
        resumed.container("captura", ["odb", "ingest", "run"])
    assert resumed.done("captura")


def test_configuracao_diferente_nao_reaproveita_recibos(tmp_path: Path) -> None:
    chain = MODULE.Chain(tmp_path)
    chain.update(config_sha256="outra-configuracao")
    with pytest.raises(ValueError, match="Configuração mudou"):
        MODULE.Chain(tmp_path)
