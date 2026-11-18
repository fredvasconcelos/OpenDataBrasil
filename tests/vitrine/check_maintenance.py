"""Confere manutenção e recuperação em contêineres descartáveis, sem dados reais."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "caddy@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0"


def docker(*args: str) -> str:
    """Executa Docker sem interpolação pelo shell."""
    return subprocess.check_output(  # noqa: S603 -- argumentos locais controlados, sem shell
        [shutil.which("docker") or "/usr/bin/docker", *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def main() -> None:  # noqa: PLR0915 -- cenário sequencial de queda e recuperação no mesmo ambiente
    """Exercita respostas HTML/JSON, retorno normal e falhas do upstream."""
    name = f"odb-maintenance-{uuid.uuid4().hex[:10]}"
    checks = 0
    with tempfile.TemporaryDirectory(prefix=name) as temporary:
        work = Path(temporary)
        assets = work / "maintenance"
        shutil.copytree(ROOT / "infrastructure/vitrine/maintenance", assets)
        (assets / "enabled").unlink(missing_ok=True)
        upstream = work / "upstream.Caddyfile"
        upstream.write_text("""{
 admin off
}
:3000 {
 @falha path /fail /odb-api/busy /_next/fail
 respond @falha "falha de teste" 503
 @export path /odb-api/exports
 header @export Content-Type text/csv
 respond @export "a,b" 200
 respond "normal" 200
}
""")
        proxy = name + "-proxy"
        portal = name + "-portal"
        try:
            docker("network", "create", name)
            docker(
                "run",
                "-d",
                "--name",
                portal,
                "--network",
                name,
                "--network-alias",
                "portal",
                "-v",
                f"{upstream}:/etc/caddy/Caddyfile:ro",
                IMAGE,
            )
            docker(
                "run",
                "-d",
                "--name",
                proxy,
                "--network",
                name,
                "-p",
                "127.0.0.1::80",
                "-v",
                f"{ROOT / 'infrastructure/vitrine/Caddyfile'}:/etc/caddy/Caddyfile:ro",
                "-v",
                f"{assets}:/srv/maintenance:ro",
                IMAGE,
            )
            address = "http://" + docker("port", proxy, "80/tcp")

            def request(
                path: str, *, method: str = "GET", rsc: bool = False, html: bool = True
            ) -> tuple[int, str, dict[str, str]]:
                headers = {"Accept": "text/html" if html else "application/json"}
                if rsc:
                    headers["RSC"] = "1"
                req = Request(address + path, method=method, headers=headers)  # noqa: S310 -- serviço local descartável
                try:
                    response = urlopen(req, timeout=5)  # noqa: S310 -- URL HTTP de porta efêmera em 127.0.0.1
                except HTTPError as error:
                    response = error
                with response:
                    return response.status, response.read().decode(), dict(response.headers)

            for _ in range(40):
                try:
                    if request("/_odb/tick")[0] == 204:
                        break
                except OSError:
                    pass
                time.sleep(0.1)
            assert request("/")[:2] == (200, "normal")
            assert request("/odb-api/exports", method="POST")[:2] == (200, "a,b")
            checks += 2
            (assets / "enabled").write_text("teste local\n")
            status, body, headers = request("/")
            assert status == 503
            assert "Manutenção em andamento" in body
            assert headers.get("Cache-Control") == "no-store"
            checks += 1
            for path, method, rsc in [
                ("/fail", "GET", True),
                ("/odb-api/exports", "POST", False),
                ("/_next/fail", "GET", False),
            ]:
                status, body, headers = request(path, method=method, rsc=rsc)
                assert status == 503
                assert json.loads(body)["error"]["code"] == "service_unavailable"
                assert headers.get("Cache-Control") == "no-store"
                checks += 1
            assert request("/_odb/tick")[0] == 204
            checks += 1
            (assets / "enabled").unlink()
            assert request("/")[:2] == (200, "normal")
            checks += 1
            status, body, _ = request("/fail")
            assert status == 503
            assert "Portal temporariamente indisponível" in body
            checks += 1
            for path, rsc in [("/odb-api/busy", False), ("/fail", True)]:
                status, body, _ = request(path, rsc=rsc)
                assert status == 503
                assert json.loads(body)["error"]["code"] == "service_unavailable"
                checks += 1
            docker("stop", portal)
            status, body, _ = request("/")
            assert status == 503
            assert "Portal temporariamente indisponível" in body
            status, body, _ = request("/odb-api/exports", method="POST", html=False)
            assert status == 503
            assert json.loads(body)["error"]["code"] == "service_unavailable"
            checks += 2
            docker("start", portal)
            for _ in range(40):
                if request("/")[0] == 200:
                    break
                time.sleep(0.1)
            assert request("/")[:2] == (200, "normal")
            checks += 1
            print(f"{checks} verificações de manutenção e recuperação aprovadas.")
        finally:
            docker("rm", "-f", proxy, portal)
            docker("network", "rm", name)


if __name__ == "__main__":
    main()
