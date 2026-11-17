from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import DateTime


def _load_migration():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261112_0008_add_password_reset_invalidated_at.py"
    )
    spec = spec_from_file_location("add_password_reset_invalidated_at", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_password_reset_invalidation_migration_upgrade_and_downgrade(
    monkeypatch,
) -> None:
    migration = _load_migration()
    calls = []
    for method_name in ("add_column", "create_index", "drop_index", "drop_column"):
        monkeypatch.setattr(
            migration.op,
            method_name,
            lambda *args, _name=method_name, **kwargs: calls.append(
                (_name, args, kwargs)
            ),
        )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20261112_0007"

    add_column = next(call for call in calls if call[0] == "add_column")
    assert add_column[1][0] == "passwordResetCodes"
    column = add_column[1][1]
    assert column.name == "invalidatedAt"
    assert isinstance(column.type, DateTime)
    assert column.nullable is True
    assert column.default is None
    assert column.server_default is None

    assert (
        "create_index",
        (
            "ix_passwordResetCodes_userId_invalidatedAt",
            "passwordResetCodes",
            ["userId", "invalidatedAt"],
        ),
        {},
    ) in calls
    assert (
        "drop_index",
        ("ix_passwordResetCodes_userId_invalidatedAt",),
        {"table_name": "passwordResetCodes"},
    ) in calls
    assert (
        "drop_column",
        ("passwordResetCodes", "invalidatedAt"),
        {},
    ) in calls
