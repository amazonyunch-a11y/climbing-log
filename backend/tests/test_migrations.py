from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_rename_migration():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260915_0002_rename_climbing_session.py"
    )
    spec = spec_from_file_location("rename_climbing_session", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_stopwatch_migration():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261014_0004_add_stopwatch_sessions.py"
    )
    spec = spec_from_file_location("add_stopwatch_sessions", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rename_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = _load_rename_migration()
    renamed_tables = []
    monkeypatch.setattr(
        migration.op,
        "rename_table",
        lambda source, target: renamed_tables.append((source, target)),
    )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20260915_0001"
    assert renamed_tables == [
        ("climbinSeesion", "climbingSession"),
        ("climbingSession", "climbinSeesion"),
    ]


def test_stopwatch_migration_creates_and_drops_its_own_table(monkeypatch) -> None:
    migration = _load_stopwatch_migration()
    created_tables = []
    dropped_tables = []
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda table_name, *columns: created_tables.append(
            (table_name, [column.name for column in columns])
        ),
    )
    monkeypatch.setattr(migration.op, "drop_table", dropped_tables.append)

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20260923_0003"
    assert created_tables == [
        (
            "stopwatchSessions",
            [
                "id",
                "userId",
                "startedAt",
                "endedAt",
                "elapsedSeconds",
                "status",
                "createdAt",
                "updatedAt",
            ],
        )
    ]
    assert dropped_tables == ["stopwatchSessions"]
