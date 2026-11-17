from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import DateTime


def _load_migration():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261115_0010_add_user_email_verified_at.py"
    )
    spec = spec_from_file_location("add_user_email_verified_at", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_user_email_verified_at_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = _load_migration()
    calls = []
    for method_name in ("add_column", "execute", "drop_column"):
        monkeypatch.setattr(
            migration.op,
            method_name,
            lambda *args, _name=method_name, **kwargs: calls.append(
                (_name, args, kwargs)
            ),
        )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20261115_0009"

    add_column = next(call for call in calls if call[0] == "add_column")
    assert add_column[1][0] == "user"
    column = add_column[1][1]
    assert column.name == "emailVerifiedAt"
    assert isinstance(column.type, DateTime)
    assert column.nullable is True
    assert column.default is None
    assert column.server_default is None

    execute = next(call for call in calls if call[0] == "execute")
    statement = execute[1][0]
    assert 'UPDATE "user"' in statement
    assert '"emailVerifiedAt" IS NULL' in statement
    assert "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'" in statement

    assert (
        "drop_column",
        ("user", "emailVerifiedAt"),
        {},
    ) in calls
