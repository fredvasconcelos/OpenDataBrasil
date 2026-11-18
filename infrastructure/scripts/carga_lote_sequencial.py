"""Executa um lote manifestado em sequência, sem ativar release nem depender de IA."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
DOCKER = shutil.which("docker") or "/usr/bin/docker"


class Batch:
    """Fixa seleção, imagem e recibos para retomar somente etapas concluídas."""

    def __init__(self, manifest_path: Path, destination: Path) -> None:
        """Recusa recibos de outra seleção ou arquivos alterados desde o preflight."""
        self.destination = destination.resolve()
        self.destination.mkdir(parents=True, exist_ok=True)
        self.path = self.destination / "estado.json"
        content = manifest_path.read_bytes()
        self.manifest = json.loads(content)
        self.fingerprint = hashlib.sha256(content).hexdigest()
        self.state: dict[str, Any] = (
            json.loads(self.path.read_text()) if self.path.exists() else {"etapas": {}}
        )
        if self.state.get("manifesto_sha256", self.fingerprint) != self.fingerprint:
            raise ValueError("Manifesto mudou: use outro destino e revise os recibos")
        self.name = self.manifest["lote"]
        if not re.fullmatch(r"[a-z0-9-]{1,40}", self.name):
            raise ValueError("Nome de lote inválido")
        self.datasets = [m["dataset"] for m in self.manifest["medidas"]]
        if not self.datasets or len(self.datasets) != len(set(self.datasets)):
            raise ValueError("O manifesto exige datasets únicos e uma seleção não vazia")
        self.env = {
            **os.environ,
            "ODB_IMAGE_TAG": self.manifest["imagem_tag"],
            "ODB_BACKUP_KEEP_DUMPS": "1000000",
        }
        self.verify_files()

    def verify_files(self) -> None:
        """Confere os bytes dos contratos, configurações e provas oficiais do lote."""
        for relative, expected in self.manifest["arquivos_sha256"].items():
            actual = hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Arquivo mudou desde o preflight: {relative}")

    def update(self, **values: Any) -> None:
        """Persiste o estado por troca atômica antes e depois de cada comando."""
        self.state.update(values)
        self.state.update(
            manifesto_sha256=self.fingerprint,
            atualizado_em=datetime.now(UTC).isoformat(),
            pid=os.getpid(),
        )
        temporary = self.path.with_suffix(".part")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(self.path)

    def compose(self, *command: str) -> list[str]:
        """Usa apenas o worker local, sem recriar banco ou migrações em uso."""
        return [
            DOCKER,
            "compose",
            "--profile",
            "data",
            "run",
            "--rm",
            "--no-deps",
            "--name",
            f"odb-{self.name}-{command[1]}",
            "worker",
            *command,
        ]

    def execute(self, stage: str, command: list[str]) -> None:
        """Conserva logs e recibos; uma falha interrompe as etapas dependentes."""
        if self.state["etapas"].get(stage, {}).get("codigo") == 0:
            return
        self.verify_files()
        self.update(fase=stage, erro=None)
        with (self.destination / f"{stage}.log").open("a") as log:
            result = subprocess.run(  # noqa: S603 - argumentos internos, sem shell.
                command,
                cwd=PROJECT,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        self.state["etapas"][stage] = {
            "codigo": result.returncode,
            "fim": datetime.now(UTC).isoformat(),
        }
        self.update()
        if result.returncode:
            raise RuntimeError(f"Lote {self.name}: {stage} falhou; consulte {stage}.log")

    def run(self) -> None:
        """Captura, Silver, candidata, release check e backup; aguarda revisão humana."""
        image = subprocess.run(  # noqa: S603 - inspeciona somente a imagem local declarada.
            [
                DOCKER,
                "image",
                "inspect",
                "--format",
                "{{.Id}}",
                f"opendatabrasil/odb:{self.manifest['imagem_tag']}",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if image != self.manifest["imagem_id"]:
            raise ValueError("Imagem local difere da fixada no manifesto; revise o lote")
        for dataset in self.datasets:
            self.execute(f"captura_{dataset}", self.compose("odb", "ingest", "run", dataset))
        self.execute("silver", self.compose("odb", "silver", "build", *self.datasets))
        self.execute("gold", self.compose("odb", "gold", "build"))
        output = (self.destination / "gold.log").read_text()
        summary = None
        decoder = json.JSONDecoder()
        for match in re.finditer(r"(?m)^\{\n", output):
            candidate, _ = decoder.raw_decode(output[match.start() :])
            if candidate.get("status") in {"succeeded", "skipped"}:
                summary = candidate
        if summary is None or not summary.get("release"):
            raise RuntimeError("Gold sem candidata concluída; confira gold.log")
        release = summary["release"]["release_id"]
        (self.destination / "gold.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )
        self.update(release_candidato=release)
        self.execute("release_check", self.compose("odb", "release", "check", release))
        self.execute("backup", [str(PROJECT / "infrastructure/scripts/backup.sh"), "--verify"])
        self.update(fase="aguardando_conferencia_final", erro=None)


def main() -> None:
    """Mantém uma única cadeia por destino e imprime o estado sem acessar segredos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--destino", type=Path, required=True)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print((args.destino / "estado.json").read_text())
        return
    args.destino.mkdir(parents=True, exist_ok=True)
    with (args.destino / "pipeline.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("O lote já está em execução; consulte --status") from None
        batch = Batch(args.manifesto, args.destino)
        try:
            batch.run()
        except Exception as exc:
            batch.update(fase="falha", erro=str(exc))
            raise


if __name__ == "__main__":
    main()
