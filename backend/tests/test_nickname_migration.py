import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20261110_0006_unique_user_nickname.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("nickname_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_user_table(engine):
    metadata = sa.MetaData()
    table = sa.Table(
        "user",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nickname", sa.String),
    )
    metadata.create_all(engine)
    return table


def test_nickname_migration_upgrade_and_downgrade(monkeypatch) -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    table = legacy_user_table(engine)
    migration = load_migration()

    with engine.begin() as connection:
        connection.execute(table.insert().values(id=3, nickname="climber01"))

    with engine.begin() as connection:
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
    assert any(
        constraint["name"] == "uq_user_nickname"
        for constraint in sa.inspect(engine).get_unique_constraints("user")
    )
    with engine.connect() as connection:
        assert connection.execute(sa.select(table.c.nickname).where(table.c.id == 3)).scalar_one() == "climber01"

    with engine.begin() as connection:
        connection.execute(table.insert().values(id=1, nickname="Climber01"))
    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(table.insert().values(id=2, nickname="Climber01"))

    with engine.begin() as connection:
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.downgrade()
    assert not sa.inspect(engine).get_unique_constraints("user")
    with engine.begin() as connection:
        connection.execute(table.insert().values(id=2, nickname="Climber01"))


def test_nickname_migration_stops_on_existing_duplicates(monkeypatch) -> None:
    engine = sa.create_engine("sqlite+pysqlite://")
    table = legacy_user_table(engine)
    migration = load_migration()
    with engine.begin() as connection:
        connection.execute(table.insert(), [
            {"id": 1, "nickname": "Climber01"},
            {"id": 2, "nickname": "Climber01"},
        ])
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        with pytest.raises(RuntimeError, match="Climber01"):
            migration.upgrade()

    assert not sa.inspect(engine).get_unique_constraints("user")
