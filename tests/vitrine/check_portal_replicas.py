"""Confere descoberta DNS e queda de réplica com o Caddy real, em pilha descartável."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "caddy@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0"


def docker(*args: str) -> str:
    """Executa somente argumentos locais controlados, sem interpolação pelo shell."""
    return subprocess.check_output(  # noqa: S603 -- cenário local controlado, sem shell
        [shutil.which("docker") or "/usr/bin/docker", *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def main() -> None:
    """Sobe três réplicas saudáveis e mantém respostas 200 após parar uma delas."""
    name = f"odb-replicas-{uuid.uuid4().hex[:10]}"
    with tempfile.TemporaryDirectory(prefix=name) as temporary:
        work = Path(temporary)
        (work / "logs").mkdir(mode=0o777)
        caddyfile = ROOT / "infrastructure/vitrine/Caddyfile"
        upstream = work / "upstream.Caddyfile"
        upstream.write_text("""{
 admin off
}
:3000 {
 respond "{env.HOSTNAME}" 200
}
""")
        compose = work / "compose.json"
        health = {
            "test": ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:3000/"],
            "interval": "1s",
            "timeout": "2s",
            "retries": 20,
        }
        compose.write_text(
            json.dumps(
                {
                    "services": {
                        "portal": {
                            "image": IMAGE,
                            "volumes": [f"{upstream}:/etc/caddy/Caddyfile:ro"],
                            "healthcheck": health,
                            "deploy": {"replicas": 3},
                        },
                        "proxy": {
                            "image": IMAGE,
                            "ports": ["127.0.0.1::80"],
                            "volumes": [
                                f"{caddyfile}:/etc/caddy/Caddyfile:ro",
                                f"{work / 'logs'}:/var/log/caddy",
                            ],
                            "depends_on": {"portal": {"condition": "service_healthy"}},
                        },
                    }
                }
            )
        )
        command = ("compose", "--project-name", name, "--file", str(compose))
        try:
            docker(*command, "up", "--detach", "--wait", "--wait-timeout", "60")
            ids = docker(*command, "ps", "--quiet", "portal").splitlines()
            assert len(ids) == 3, ids
            for identifier in ids:
                assert (
                    docker("inspect", "--format", "{{.State.Health.Status}}", identifier)
                    == "healthy"
                )
            port = docker(*command, "port", "proxy", "80")
            base = f"http://{port}"

            def visit() -> str:
                with urlopen(base + "/dashboard", timeout=10) as response:  # noqa: S310 -- origem local criada acima
                    assert response.status == 200
                    body: bytes = response.read()
                    return body.decode().strip()

            seen = {visit() for _ in range(60)}
            assert len(seen) == 3, seen
            stopped = docker("inspect", "--format", "{{.Config.Hostname}}", ids[0])
            docker("stop", ids[0])
            # O plano permite falhas transitórias enquanto DNS e checagem passiva
            # retiram o destino. O regime estável, após essa janela, exige só 200.
            deadline = time.monotonic() + 5
            transient = 0
            while time.monotonic() < deadline:
                try:
                    visit()
                except HTTPError as error:
                    if error.code not in {502, 503, 504}:
                        raise AssertionError(error.code) from error
                    transient += 1
                time.sleep(0.1)
            remaining = {visit() for _ in range(60)}
            assert stopped not in remaining, (stopped, remaining)
            assert len(remaining) == 2, remaining
            print(
                "Aprovado: Compose aguardou 3 réplicas; DNS distribuiu entre as 3; "
                "60 respostas 200 em regime após parar uma réplica; "
                f"2 destinos restantes; falhas transitórias: {transient}."
            )
        finally:
            docker(*command, "down", "--remove-orphans", "--volumes")


if __name__ == "__main__":
    main()
