from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import Enum


def _load_migration():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261115_0009_add_password_reset_purpose.py"
    )
    spec = spec_from_file_location("add_password_reset_purpose", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_password_reset_purpose_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = _load_migration()
    calls = []
    bind = object()

    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    for method_name in ("add_column", "execute", "alter_column", "drop_column"):
        monkeypatch.setattr(
            migration.op,
            method_name,
            lambda *args, _name=method_name, **kwargs: calls.append(
                (_name, args, kwargs)
            ),
        )
    monkeypatch.setattr(
        migration.purpose_enum,
        "create",
        lambda actual_bind, **kwargs: calls.append(
            ("create_enum", (actual_bind,), kwargs)
        ),
    )
    monkeypatch.setattr(
        migration.purpose_enum,
        "drop",
        lambda actual_bind, **kwargs: calls.append(
            ("drop_enum", (actual_bind,), kwargs)
        ),
    )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20261112_0008"
    assert migration.purpose_enum.name == "password_reset_purpose"
    assert set(migration.purpose_enum.enums) == {
        "password_reset",
        "email_verification",
    }
    assert calls[0] == ("create_enum", (bind,), {"checkfirst": False})

    add_column = next(call for call in calls if call[0] == "add_column")
    assert add_column[1][0] == "passwordResetCodes"
    column = add_column[1][1]
    assert column.name == "purpose"
    assert isinstance(column.type, Enum)
    assert column.nullable is True

    execute = next(call for call in calls if call[0] == "execute")
    assert "password_reset" in execute[1][0]
    assert "WHERE purpose IS NULL" in execute[1][0]

    alter = next(call for call in calls if call[0] == "alter_column")
    assert alter[1] == ("passwordResetCodes", "purpose")
    assert alter[2]["nullable"] is False
    assert "password_reset" in str(alter[2]["server_default"])

    assert (
        "drop_column",
        ("passwordResetCodes", "purpose"),
        {},
    ) in calls
    assert calls[-1] == ("drop_enum", (bind,), {"checkfirst": False})
