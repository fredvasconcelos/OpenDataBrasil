"""Aplicação FastAPI (ADR-0009).

Execução: ``uvicorn --factory odb_api.app:create_default_app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from odb_api import errors
from odb_api.config import ApiSettings
from odb_api.deps import ApiDeps, build_deps
from odb_api.middleware import RateLimiter, make_middleware
from odb_api.routes import catalog, kpi, query, territory
from odb_api.routes.common import Deps
from odb_common.logging import configure_logging
from odb_common.settings import Settings

DESCRIPTION = (
    "Consulta aos dados analíticos publicados (release Gold em Delta Lake). "
    "Nenhuma rota aceita SQL ou caminhos: as consultas são estruturadas e passam "
    "pelas regras semânticas do catálogo. Toda resposta informa o release usado."
)


def create_app(deps: ApiDeps | None, settings: ApiSettings | None = None) -> FastAPI:
    """Aplicação com os componentes informados (os testes injetam os seus).

    ``deps=None`` monta só as rotas, para gerar o contrato OpenAPI.
    """
    settings = settings or (deps.settings if deps else ApiSettings())

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if deps is not None:
            deps.close()

    app = FastAPI(
        title="Plataforma de Dados Abertos do Brasil — API",
        version="0.1.0",
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.deps = deps
    errors.install(app)
    app.middleware("http")(make_middleware(RateLimiter(settings.rate_limit_per_minute)))
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "If-None-Match"],
        expose_headers=["X-ODB-Release", "ETag", "Content-Disposition"],
    )
    for router in (catalog.router, territory.router, kpi.router, query.router):
        app.include_router(router)

    @app.get("/health", tags=["operação"], summary="Saúde do serviço")
    def health(d: Deps) -> dict[str, str]:
        """PostgreSQL acessível e release ativo resolvido."""
        d.catalog.ping()
        return {"status": "ok", "release_id": d.resolver.current().release_id}

    return app


def create_default_app() -> FastAPI:
    """Aplicação com a configuração do ambiente (``ODB_*`` e ``ODB_API_*``)."""
    settings = Settings()
    configure_logging(settings.log_level)
    return create_app(build_deps(settings))


def write_openapi(path: str) -> None:
    """Grava o contrato OpenAPI (``python -m odb_api.app <arquivo>``)."""
    import json  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    spec = create_app(None).openapi()
    Path(path).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import sys

    write_openapi(sys.argv[1])
