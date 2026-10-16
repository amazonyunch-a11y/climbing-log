import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def client_and_engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def signup(client: TestClient, email: str = "user@example.com"):
    return client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "correct-password",
            "nickname": "climber01",
        },
    )


def login(client: TestClient, email: str = "user@example.com", password: str = "correct-password"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def test_signup_success_response(client_and_engine) -> None:
    client, _ = client_and_engine
    response = signup(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "nickname", "created_at"}
    assert body["email"] == "user@example.com"
    assert body["nickname"] == "climber01"
    assert body["created_at"].endswith("Z")
    assert "password" not in body


def test_signup_rejects_duplicate_email(client_and_engine) -> None:
    client, _ = client_and_engine
    assert signup(client).status_code == 201

    response = signup(client)

    assert response.status_code == 409


def test_signup_stores_a_password_hash(client_and_engine) -> None:
    client, engine = client_and_engine
    signup(client)

    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        assert user.passwordHash != "correct-password"
        assert user.passwordHash.startswith("$argon2")


def test_login_returns_bearer_access_token(client_and_engine) -> None:
    client, _ = client_and_engine
    signup(client)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type"}
    assert body["access_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.parametrize(
    ("email", "password"),
    [("missing@example.com", "correct-password"), ("user@example.com", "wrong-password")],
)
def test_login_rejects_invalid_credentials(client_and_engine, email: str, password: str) -> None:
    client, _ = client_and_engine
    signup(client)

    response = login(client, email=email, password=password)

    assert response.status_code == 401


def test_get_me_with_valid_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine
    signup(client)
    token = login(client).json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "email": "user@example.com", "nickname": "climber01"}


@pytest.mark.parametrize("headers", [None, {"Authorization": "Bearer invalid-token"}])
def test_get_me_rejects_missing_or_invalid_bearer_token(client_and_engine, headers) -> None:
    client, _ = client_and_engine

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


def test_logout_returns_no_content(client_and_engine) -> None:
    client, _ = client_and_engine
    signup(client)
    token = login(client).json()["access_token"]

    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204
    assert response.content == b""
