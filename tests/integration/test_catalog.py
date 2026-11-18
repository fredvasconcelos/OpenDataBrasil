import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from odb_catalog import PostgresAdvisoryLock, tracked_run
from odb_catalog.migrate import current_revision, downgrade, head_revision, upgrade
from odb_common.locking import LockUnavailableError
from odb_common.settings import Settings

pytestmark = pytest.mark.integration


def test_migration_roundtrip(engine: Engine, pg_settings: Settings) -> None:
    assert current_revision(engine) == head_revision() == "0005"
    url = pg_settings.postgres_url()
    downgrade(url, "base")
    assert current_revision(engine) is None
    upgrade(url)
    assert current_revision(engine) == "0005"


def test_tracked_run_success_and_failure(engine: Engine) -> None:
    with tracked_run(engine, "test.ok", "abc123", {"k": 1}) as run_ok:
        pass
    with pytest.raises(RuntimeError), tracked_run(engine, "test.fail", "abc123") as run_fail:
        raise RuntimeError("boom")
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT run_id::text, status || ':' || coalesce(error, '') "
                "FROM operations.pipeline_run"
            )
        ).all()
    rows = {str(r[0]): str(r[1]) for r in result}
    assert rows[run_ok] == "succeeded:"
    assert rows[run_fail] == "failed:RuntimeError: boom"


def test_advisory_lock_is_exclusive_across_sessions(engine: Engine) -> None:
    lock_a, lock_b = PostgresAdvisoryLock(engine), PostgresAdvisoryLock(engine)
    with lock_a.hold("file:///lakehouse/gold/t"):
        with pytest.raises(LockUnavailableError), lock_b.hold("file:///lakehouse/gold/t"):
            pass
        with lock_b.hold("file:///lakehouse/gold/other"):
            pass
    with lock_b.hold("file:///lakehouse/gold/t"):
        pass


def test_pipeline_role_can_write_operations(pipeline_engine: Engine) -> None:
    with tracked_run(pipeline_engine, "test.role", "abc") as run_id:
        assert run_id


def test_reader_role_is_read_only(reader_engine: Engine) -> None:
    with reader_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM publication.release")).scalar() == 0
    with pytest.raises(ProgrammingError, match="permission denied"), reader_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO publication.release (release_id, scope, code_version, created_by) "
                "VALUES (gen_random_uuid(), 'x', 'v', 'reader')"
            )
        )
    with (
        pytest.raises(ProgrammingError, match="permission denied"),
        reader_engine.connect() as conn,
    ):
        conn.execute(text("SELECT * FROM operations.pipeline_run"))


def test_database_enforces_single_active_release(engine: Engine) -> None:
    insert = text(
        "INSERT INTO publication.release (release_id, scope, status, code_version, created_by, "
        "activated_at) VALUES (gen_random_uuid(), 'dup', 'active', 'v', 't', now())"
    )
    with engine.begin() as conn:
        conn.execute(insert)
    with (
        pytest.raises(IntegrityError, match="release_one_active_per_scope"),
        engine.begin() as conn,
    ):
        conn.execute(insert)


def test_application_roles_can_read_revision(
    pipeline_engine: Engine, reader_engine: Engine
) -> None:
    """O `odb doctor` roda com o role do serviço, não com odb_owner."""
    assert current_revision(pipeline_engine) == head_revision()
    assert current_revision(reader_engine) == head_revision()
