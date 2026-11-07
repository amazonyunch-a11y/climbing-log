from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_migration():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261023_0005_link_stopwatch_sessions.py"
    )
    spec = spec_from_file_location("link_stopwatch_sessions", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stopwatch_session_link_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = _load_migration()
    calls = []

    for method_name in (
        "add_column",
        "create_foreign_key",
        "create_unique_constraint",
        "create_index",
        "execute",
        "alter_column",
        "create_check_constraint",
        "drop_constraint",
        "drop_column",
        "drop_index",
    ):
        monkeypatch.setattr(
            migration.op,
            method_name,
            lambda *args, _method_name=method_name, **kwargs: calls.append(
                (_method_name, args, kwargs)
            ),
        )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20261014_0004"
    assert (
        "create_foreign_key",
        (
            "fk_stopwatchSessions_climbingSessionId_climbingSession",
            "stopwatchSessions",
            "climbingSession",
            ["climbingSessionId"],
            ["id"],
        ),
        {"ondelete": "SET NULL"},
    ) in calls
    assert (
        "create_unique_constraint",
        ("uq_stopwatchSessions_climbingSessionId", "stopwatchSessions", ["climbingSessionId"]),
        {},
    ) in calls
    assert ("execute", ('UPDATE "climbingSession" SET "durationSource" = \'manual\' WHERE "durationSource" IS NULL',), {}) in calls
    assert (
        "drop_constraint",
        ("fk_stopwatchSessions_climbingSessionId_climbingSession", "stopwatchSessions"),
        {"type_": "foreignkey"},
    ) in calls
