from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_migration():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261112_0007_add_password_reset_codes.py"
    )
    spec = spec_from_file_location("add_password_reset_codes", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_password_reset_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = _load_migration()
    calls = []
    for method_name in (
        "add_column",
        "execute",
        "alter_column",
        "create_table",
        "create_index",
        "drop_index",
        "drop_table",
        "drop_column",
    ):
        monkeypatch.setattr(
            migration.op,
            method_name,
            lambda *args, _name=method_name, **kwargs: calls.append(
                (_name, args, kwargs)
            ),
        )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20261110_0006"
    assert any(call[0] == "create_table" and call[1][0] == "passwordResetCodes" for call in calls)
    assert ("drop_table", ("passwordResetCodes",), {}) in calls
    assert ("drop_column", ("user", "authVersion"), {}) in calls
    migration_source = Path(migration.__file__).read_text(encoding="utf-8")
    assert "rawCode" not in migration_source
