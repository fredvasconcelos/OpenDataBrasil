"""Logs estruturados em JSON (uma linha por evento, timestamps em UTC).

O contexto de execução (``run_id``, ``dataset_id``, etc.) é propagado por
``contextvars``, então fica correto também em threads e em código assíncrono.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
from collections.abc import Iterator, Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, TextIO

_context: ContextVar[Mapping[str, Any] | None] = ContextVar("odb_log_context", default=None)

# Atributos padrão de LogRecord que não devem ser repetidos como campos extras.
_RESERVED = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys() | {"message", "asctime"}
)

# Nomes de campos cujo valor nunca deve aparecer no log.
_SENSITIVE_KEYS = frozenset({"password", "senha", "secret", "token", "authorization", "dsn"})


def _redact(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(s in lowered for s in _SENSITIVE_KEYS):
        return "***"
    return value


class JsonFormatter(logging.Formatter):
    """Formata cada registro como um objeto JSON em uma única linha."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializa o registro, o contexto ativo e os campos extras."""
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in (_context.get() or {}).items():
            payload[key] = _redact(key, value)
        for key, value in vars(record).items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = _redact(key, value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Configura o logger raiz com saída JSON. Pode ser chamada mais de uma vez."""
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())


@contextlib.contextmanager
def log_context(**fields: Any) -> Iterator[None]:
    """Acrescenta campos a todos os logs emitidos dentro do bloco."""
    current = dict(_context.get() or {})
    current.update(fields)
    token = _context.set(current)
    try:
        yield
    finally:
        _context.reset(token)
