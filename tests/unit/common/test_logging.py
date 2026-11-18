import io
import json
import logging

from odb_common.logging import configure_logging, log_context


def _emit(**extra: object) -> dict[str, object]:
    stream = io.StringIO()
    configure_logging("DEBUG", stream=stream)
    logging.getLogger("odb.test").info("evento %s", "x", extra=extra)
    parsed: dict[str, object] = json.loads(stream.getvalue().strip().splitlines()[-1])
    return parsed


def test_json_line_with_utc_timestamp() -> None:
    record = _emit()
    assert record["msg"] == "evento x"
    assert record["level"] == "INFO"
    assert str(record["ts"]).endswith("+00:00")


def test_context_and_extras_and_redaction() -> None:
    with log_context(run_id="r1"):
        record = _emit(dataset_id="d1", pg_password="secreto")
    assert record["run_id"] == "r1"
    assert record["dataset_id"] == "d1"
    assert record["pg_password"] == "***"
    assert "run_id" not in _emit()


def test_exception_serialized() -> None:
    stream = io.StringIO()
    configure_logging(stream=stream)
    try:
        raise RuntimeError("falhou")
    except RuntimeError:
        logging.getLogger("odb.test").exception("erro")
    assert "RuntimeError: falhou" in json.loads(stream.getvalue())["exc"]
