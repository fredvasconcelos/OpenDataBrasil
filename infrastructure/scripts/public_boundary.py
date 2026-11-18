"""Impede que conteúdo interno ou segredos entrem na distribuição pública.

Examina o índice completo, que é a árvore efetiva do próximo commit. Arquivos locais
não rastreados não são lidos, e links simbólicos não são seguidos. CI e pre-commit
executam esta mesma entrada, com Gitleaks fixado e sem acesso à rede.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

# Gitleaks 8.24.3, publicado em 11/04/2025; imagem oficial fixada por digest.
GITLEAKS_IMAGE = (
    "ghcr.io/gitleaks/gitleaks@sha256:"
    "e1b35e12a8c6fa8901f060459cfb6b2fc4c484d3afbe3b029733a3bbfab07055"
)
ASCII_CONTROL_END = 32
INTERNAL_DIRECTORIES = (
    "docs/relatorios",
    "docs-local",
    "design-system/portal",
    "design-system/reference",
    ".design-sync",
    ".ds-sync",
    "ds-bundle",
    "backups",
    "data",
    "lakehouse",
)
INTERNAL_FILES = frozenset(
    {
        "design-system/README.md",
        "design-system/VERSION",
        "docs/architecture/plano-desempenho-portal.md",
        "docs/architecture/plano-vitrine-servidor-domestico.md",
        "docs/architecture/replanejamento-2026-11.md",
        "docs/runbooks/checklist-pre-lancamento.md",
        "docs/runbooks/carga-agro-sequencial.md",
        "docs/runbooks/carga-lote-manifestado.md",
        "docs/development/plano-apoio-textos-mobile.md",
        "docs/development/plano-periodo-acumular-tabela.md",
    }
)
CONTENT_RULES = (
    ("endereço da rede de operação", re.compile(rb"\b192[.]168[.]\d{1,3}[.]\d{1,3}\b")),
    ("atalho ou chave do ambiente de operação", re.compile(rb"odb[-_]homolog", re.I)),
    ("usuário de acesso ao servidor", re.compile(rb"ubuntu" rb"@", re.I)),
    ("endereço de túnel temporário", re.compile(rb"trycloud" rb"flare", re.I)),
    (
        "artefato interno de design",
        re.compile(rb"claude[.]ai/(?:artifact|design|project|chat|share)", re.I),
    ),
    ("caminho pessoal", re.compile(rb"/home/[^/\s]+/(?:dev|[.]ssh|[.]claude|[.]codex)(?:/|\b)")),
    ("chave privada", re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")),
)


def path_problems(name: str, mode: str) -> list[str]:
    """Classifica caminhos proibidos sem abrir o arquivo ou seguir links."""
    path = PurePosixPath(name)
    normalized = name.casefold()
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or any(ord(c) < ASCII_CONTROL_END for c in name)
    ):
        return ["caminho inválido"]
    problems = []
    if mode not in {"100644", "100755"}:
        problems.append("link simbólico ou submódulo não permitido")
    if any(
        normalized == p.casefold() or normalized.startswith(p.casefold() + "/")
        for p in INTERNAL_DIRECTORIES
    ) or normalized in {p.casefold() for p in INTERNAL_FILES}:
        problems.append("material interno")
    if any(p.casefold().startswith("evidencias") for p in path.parts):
        problems.append("evidência operacional")
    basename = path.name.casefold()
    if basename == "agents.md" or (basename.startswith(".env") and basename != ".env.example"):
        problems.append("configuração local ou continuidade interna")
    if path.suffix.casefold() in {".dump", ".pem", ".key"}:
        problems.append("backup ou credencial")
    return problems


def content_problems(data: bytes) -> list[str]:
    """Retorna regra e linha, sem revelar o conteúdo que motivou o bloqueio."""
    return [
        f"{label}, linha {data.count(b'\n', 0, match.start()) + 1}"
        for label, pattern in CONTENT_RULES
        if (match := pattern.search(data))
    ]


def executable(name: str) -> str:
    """Resolve a ferramenta local e falha quando ela não está disponível."""
    found = shutil.which(name)
    if found is None:
        raise FileNotFoundError(name)
    return found


def git(root: Path, *arguments: str, input_data: bytes | None = None) -> bytes:
    """Lê metadados e blobs locais por argumentos separados, sem shell."""
    return subprocess.run(  # noqa: S603 - executável fixo e argumentos locais, sem shell
        [executable("git"), "-C", str(root), *arguments],
        check=True,
        input=input_data,
        capture_output=True,
    ).stdout


def snapshot_index(root: Path, snapshot: Path) -> tuple[int, list[str]]:
    """Materializa somente blobs do índice para a varredura isolada de segredos."""
    entries: list[tuple[str, str]] = []
    problems: list[str] = []
    for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8")
        found = path_problems(name, mode)
        if stage != "0":
            found.append("conflito não resolvido no índice")
        problems.extend(f"{name}: {reason}" for reason in found)
        if not found:
            entries.append((name, oid))
    if not entries:
        problems.append(
            "índice vazio: adicione os arquivos públicos explicitamente antes de conferir"
        )
    for name, oid in entries:
        data = git(root, "cat-file", "blob", oid)
        problems.extend(f"{name}: {reason}" for reason in content_problems(data))
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return len(entries), problems


def scan_secrets(snapshot: Path) -> int:
    """Executa Gitleaks na cópia do índice, sem rede, com resultados ocultados."""
    result = subprocess.run(  # noqa: S603 - imagem fixada, sem shell e sem rede
        [
            executable("docker"),
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{snapshot}:/repo:ro",
            GITLEAKS_IMAGE,
            "detect",
            "--no-git",
            "--source=/repo",
            "--redact=100",
            "--no-banner",
            "--exit-code=1",
        ],
        check=False,
    )
    return result.returncode


def main() -> int:
    """Recusa a publicação quando qualquer etapa da conferência falhar."""
    try:
        root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
        with tempfile.TemporaryDirectory(prefix="odb-public-boundary-") as temporary:
            snapshot = Path(temporary)
            count, problems = snapshot_index(root, snapshot)
            if problems:
                print("Distribuição pública bloqueada:", file=sys.stderr)
                for problem in problems:
                    print(f"- {problem}", file=sys.stderr)
                return 1
            if scan_secrets(snapshot):
                print(
                    "Distribuição bloqueada: a varredura de segredos não foi aprovada.",
                    file=sys.stderr,
                )
                return 1
        print(f"Distribuição pública conferida: {count} arquivos do índice e Gitleaks aprovados.")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(
            f"Não foi possível concluir o guarda de fronteira ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
