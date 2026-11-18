"""Processa sequencialmente os recortes agropecuários cuja captura já terminou."""

from __future__ import annotations

import shutil
import subprocess
import time

from odb_catalog import make_engine
from odb_catalog.ingestion import PostgresIngestionRegistry
from odb_common.settings import load_settings
from odb_ingestion import load_sources


def main() -> None:
    """Aguarda a Bronze de cada dataset e interrompe a cadeia em caso de falha."""
    executable = shutil.which("odb")
    if executable is None:
        raise RuntimeError("Executável odb não encontrado na imagem do worker")
    registry = PostgresIngestionRegistry(make_engine(load_settings()))
    datasets = [
        d.id
        for d in load_sources("/app/configs/sources").datasets.values()
        if str(d.silver.get("series", "")).startswith("ibge-agro-")
    ]
    for index, dataset in enumerate(datasets, 1):
        deadline = time.monotonic() + 86400
        while True:
            recent = registry.recent_ingestions(dataset_id=dataset, limit=1)
            if recent and recent[0]["status"] == "succeeded":
                break
            if recent and recent[0]["status"] not in ("running", "deferred"):
                raise RuntimeError(f"Captura não concluída: {dataset}: {recent[0]['status']}")
            if time.monotonic() > deadline:
                raise TimeoutError(f"Captura ainda pendente: {dataset}")
            time.sleep(5)
        print(f"SILVER {index}/{len(datasets)} {dataset}", flush=True)
        subprocess.run(  # noqa: S603 - id validado no catálogo local; sem shell.
            [executable, "silver", "build", dataset], check=True
        )
    print("SILVER CONCLUÍDA: todos os datasets", flush=True)


if __name__ == "__main__":
    main()
