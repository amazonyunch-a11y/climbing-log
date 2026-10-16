from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_profile_column_migration():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260923_0003_rename_user_profile_columns.py"
    )
    spec = spec_from_file_location("rename_user_profile_columns", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_user_profile_column_rename_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = _load_profile_column_migration()
    renamed_columns = []
    monkeypatch.setattr(
        migration.op,
        "alter_column",
        lambda table, column, **kwargs: renamed_columns.append(
            (table, column, kwargs["new_column_name"])
        ),
    )

    migration.upgrade()
    migration.downgrade()

    assert migration.down_revision == "20260915_0002"
    assert renamed_columns == [
        ("userProfile", "heithtCm", "heightCm"),
        ("userProfile", "weighKg", "weightKg"),
        ("userProfile", "updateAt", "updatedAt"),
        ("userProfile", "heightCm", "heithtCm"),
        ("userProfile", "weightKg", "weighKg"),
        ("userProfile", "updatedAt", "updateAt"),
    ]
