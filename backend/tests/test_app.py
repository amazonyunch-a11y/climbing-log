from app.main import app


def test_application_imports() -> None:
    assert app.title == "Climbing Log API"


def test_settings_loads_database_url(monkeypatch) -> None:
    from app.core.config import Settings

    database_url = "postgresql+psycopg://user:password@localhost:5432/climbing_log"
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = Settings(_env_file=None)

    assert settings.database_url == database_url
