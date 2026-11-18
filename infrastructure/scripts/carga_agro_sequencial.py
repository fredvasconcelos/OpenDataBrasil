"""Orquestra a carga agropecuária sem depender da sessão ou dos tokens do agente."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import threading
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
DOCKER = shutil.which("docker") or "/usr/bin/docker"
IMAGE_TAG = "agro-20261117-v2"
CONTAINERS = {
    "captura": "odb-agro-captura-20261117",
    "silver": "odb-agro-silver-20261117",
    "gold": "odb-agro-gold-20261117",
}


class Chain:
    """Mantém recibos e logs duráveis; nenhuma etapa ativa o release automaticamente."""

    def __init__(self, destination: Path, image_tag: str = IMAGE_TAG) -> None:
        """Carrega o estado anterior, conferindo a identidade da configuração."""
        self.destination = destination.resolve()
        self.destination.mkdir(parents=True, exist_ok=True)
        self.path = self.destination / "estado.json"
        self.lock = threading.Lock()
        self.env = {**os.environ, "ODB_IMAGE_TAG": image_tag, "ODB_BACKUP_KEEP_DUMPS": "1000000"}
        source = PROJECT / "configs/sources/ibge-medidas-agro.toml"
        content = source.read_bytes()
        self.datasets = [d["id"] for d in tomllib.loads(content.decode())["datasets"]]
        self.state: dict[str, Any] = (
            json.loads(self.path.read_text()) if self.path.exists() else {"etapas": {}}
        )
        fingerprint = hashlib.sha256(content).hexdigest()
        if self.state.get("config_sha256", fingerprint) != fingerprint:
            raise ValueError(
                "Configuração mudou: use outro diretório e confira os recibos anteriores"
            )
        self.update(
            config_sha256=fingerprint, datasets=self.datasets, pid=os.getpid(), imagem=image_tag
        )

    def update(self, **values: Any) -> None:
        """Grava o estado por troca atômica, inclusive quando observadores terminam juntos."""
        with self.lock:
            self.state.update(values)
            self.state["atualizado_em"] = datetime.now(UTC).isoformat()
            temporary = self.path.with_suffix(".part")
            temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n")
            temporary.replace(self.path)

    def receipt(self, stage: str, code: int) -> None:
        """Registra a saída de uma etapa sem perder o recibo das demais."""
        with self.lock:
            self.state["etapas"][stage] = {"codigo": code, "fim": datetime.now(UTC).isoformat()}
        self.update()

    def done(self, stage: str) -> bool:
        """Uma etapa só está concluída se possui recibo explícito de sucesso."""
        return self.state["etapas"].get(stage, {}).get("codigo") == 0

    def compose(self, *args: str) -> list[str]:
        """Monta apenas comandos locais, na imagem fixada para esta carga."""
        return [DOCKER, "compose", "--profile", "data", "run", "--rm", "--no-deps", *args]

    def container(self, stage: str, command: list[str], mounts: list[str] | None = None) -> None:
        """Adota um contêiner existente ou inicia a etapa, preservando a saída antes do --rm."""
        if self.done(stage):
            return
        name = CONTAINERS[stage]
        found = subprocess.run(  # noqa: S603 - argumentos internos, sem shell ou dados baixados.
            [DOCKER, "inspect", "--format", "{{.State.Running}}", name],
            capture_output=True,
            text=True,
            check=False,
        )
        if found.returncode:
            args = ["-d", "--name", name]
            for mount in mounts or []:
                args += ["-v", mount]
            subprocess.run(  # noqa: S603 - argumentos internos, sem shell ou dados baixados.
                self.compose(*args, "worker", *command),
                cwd=PROJECT,
                env=self.env,
                stdout=subprocess.DEVNULL,
                check=True,
            )
        print(f"{datetime.now(UTC).isoformat()} acompanhando {stage}: {name}", flush=True)
        with (self.destination / f"{stage}.log").open("w") as log:
            follower = subprocess.Popen(  # noqa: S603 - apenas leitura dos logs de contêiner nomeado.
                [DOCKER, "logs", "--follow", name],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            result = subprocess.run(  # noqa: S603 - argumentos internos, sem shell ou dados baixados.
                [DOCKER, "wait", name],
                capture_output=True,
                text=True,
                check=False,
            )
            follower.wait()
        code = int(result.stdout.strip()) if result.returncode == 0 else 125
        self.receipt(stage, code)
        if code:
            raise RuntimeError(f"{stage} falhou com código {code}; consulte {stage}.log")

    def command(self, stage: str, command: list[str]) -> None:
        """Executa uma conferência curta ou backup, sem esconder o código de saída."""
        if self.done(stage):
            return
        self.update(fase=stage)
        print(f"{datetime.now(UTC).isoformat()} iniciando {stage}", flush=True)
        with (self.destination / f"{stage}.log").open("w") as log:
            result = subprocess.run(  # noqa: S603 - argumentos internos, sem shell ou dados baixados.
                command,
                cwd=PROJECT,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        self.receipt(stage, result.returncode)
        if result.returncode:
            raise RuntimeError(f"{stage} falhou; consulte {stage}.log")

    def run(self) -> None:
        """Captura → Silver → Gold candidata → validação → backup; aguarda revisão final."""
        self.update(fase="captura_e_silver", erro=None)
        script = PROJECT / "infrastructure/scripts/carga_agro_silver.py"
        with ThreadPoolExecutor(max_workers=2) as pool:
            capture = pool.submit(
                self.container, "captura", ["odb", "ingest", "run", *self.datasets]
            )
            silver = pool.submit(
                self.container,
                "silver",
                ["python", "-I", "-B", "/operacao.py"],
                [f"{script}:/operacao.py:ro"],
            )
            capture.result()
            silver.result()
        self.update(fase="gold")
        self.container("gold", ["odb", "gold", "build"])
        output = (self.destination / "gold.log").read_text()
        summary = None
        for start, line in enumerate(output.splitlines(keepends=True)):
            if line == "{\n":
                summary, _ = json.JSONDecoder().raw_decode(
                    "".join(output.splitlines(keepends=True)[start:])
                )
                break
        if not summary or summary.get("status") not in ("succeeded", "skipped"):
            raise RuntimeError("Gold sem resumo de sucesso; consulte gold.log")
        (self.destination / "gold.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2)
        )
        release = summary["release"]["release_id"]
        self.update(
            release_candidato=release, observacoes=summary["rows"].get("indicator_observation")
        )
        self.command("release_check", self.compose("worker", "odb", "release", "check", release))
        self.command("backup", [str(PROJECT / "infrastructure/scripts/backup.sh"), "--verify"])
        self.update(fase="aguardando_conferencia_final", erro=None)
        print(
            f"Cadeia concluída. Release candidato {release}; "
            "ativação depende da conferência final.",
            flush=True,
        )


def main() -> None:
    """Executa sob trava local ou imprime o estado, sem acessar credenciais."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=PROJECT / "data/logs/agro-20261117")
    parser.add_argument("--status", action="store_true")
    parser.add_argument(
        "--imagem", default=IMAGE_TAG, help="Tag local da imagem revisada do worker."
    )
    args = parser.parse_args()
    if args.status:
        state = json.loads((args.destino / "estado.json").read_text())
        status = {key: value for key, value in state.items() if key != "datasets"}
        stage = state.get("fase")
        previous = state.get("etapas", {}).get(stage, {})
        if stage in CONTAINERS and previous.get("codigo") is not None:
            # O recibo anterior fica no disco até o término da tentativa atual.
            status["etapas"] = {
                **state["etapas"],
                stage: {"codigo": None, "estado": "em_execucao", "recibo_anterior": previous},
            }
        status["datasets_previstos"] = len(state.get("datasets", []))
        capture_log = args.destino / "captura.log"
        if capture_log.exists():
            events = [
                json.loads(line)
                for line in capture_log.read_text().splitlines()
                if line.startswith('{"ts":')
            ]
            status["capturas_concluidas"] = sum(
                e.get("msg") == "ingestion finished" and e.get("status") == "succeeded"
                for e in events
            )
            if events:
                status["ultimo_dataset"] = events[-1].get("dataset_id")
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    args.destino.mkdir(parents=True, exist_ok=True)
    with (args.destino / "pipeline.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A cadeia já está em execução; use --status") from None
        chain = Chain(args.destino, args.imagem)
        try:
            chain.run()
        except Exception as exc:
            chain.update(fase="falha", erro=str(exc))
            raise


if __name__ == "__main__":
    main()
