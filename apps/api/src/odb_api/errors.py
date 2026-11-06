"""Erros padronizados: ``{"error": {"code", "message"}}``."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from odb_api.exports import ExportTooLargeError
from odb_api.gold import NotFoundError
from odb_api.portal import PortalConfigError
from odb_api.release import ReleaseUnavailableError, TableNotInReleaseError
from odb_query_engine import (
    QueryEngineBusyError,
    QueryRejectedError,
    QueryTimeoutError,
)
from odb_semantics import SemanticError

logger = logging.getLogger(__name__)

# exceção → (status HTTP, código estável)
_MAP: list[tuple[type[Exception], int, str]] = [
    (SemanticError, 422, "semantic_rule"),
    (NotFoundError, 404, "not_found"),
    (TableNotInReleaseError, 404, "not_in_release"),
    (ExportTooLargeError, 413, "too_large"),
    (QueryRejectedError, 400, "rejected"),
    (QueryTimeoutError, 504, "timeout"),
    (QueryEngineBusyError, 503, "busy"),
    (ReleaseUnavailableError, 503, "release_unavailable"),
]


def error_response(status: int, code: str, message: str) -> JSONResponse:
    """Resposta de erro no formato da API."""
    headers = {"Retry-After": "1"} if status in {429, 503} else None
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status, headers=headers
    )


def install(app: FastAPI) -> None:
    """Registra os tratadores."""
    for exc_type, status, code in _MAP:

        async def handler(
            _request: Request, exc: Exception, status: int = status, code: str = code
        ) -> JSONResponse:
            return error_response(status, code, str(exc))

        app.add_exception_handler(exc_type, handler)

    async def invalid(_request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)  # noqa: S101
        parts = [
            f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg')}" for e in exc.errors()
        ]
        return error_response(422, "invalid_request", "; ".join(parts))

    async def portal(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("portal config incoherent with release", extra={"error": str(exc)})
        return error_response(500, "portal_config", str(exc))

    app.add_exception_handler(RequestValidationError, invalid)
    app.add_exception_handler(PortalConfigError, portal)
