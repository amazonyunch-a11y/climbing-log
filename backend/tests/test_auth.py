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
from tests.auth_helpers import mark_email_verified


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


def signup(client: TestClient, email: str = "user@example.com", nickname: str = "Climber01"):
    return client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "correct-password",
            "nickname": nickname,
        },
    )


def login(client: TestClient, email: str = "user@example.com", password: str = "correct-password"):
    mark_email_verified(email)
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def test_signup_success_response(client_and_engine) -> None:
    client, engine = client_and_engine
    response = signup(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "nickname", "created_at"}
    assert body["email"] == "user@example.com"
    assert body["nickname"] == "Climber01"
    assert body["created_at"].endswith("Z")
    assert "password" not in body
    with Session(engine) as db:
        assert db.get(User, body["id"]).emailVerifiedAt is None


def test_login_rejects_unverified_user(client_and_engine) -> None:
    client, _ = client_and_engine
    assert signup(client).status_code == 201

    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correct-password"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "message": "이메일 인증을 완료한 후 로그인해 주세요."
    }


def test_signup_rejects_duplicate_email(client_and_engine) -> None:
    client, _ = client_and_engine
    assert signup(client).status_code == 201

    response = signup(client)

    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


def test_signup_rejects_duplicate_nickname(client_and_engine) -> None:
    client, _ = client_and_engine
    assert signup(client).status_code == 201

    response = signup(client, email="another@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "Nickname is already taken"


def test_signup_preserves_case_and_trims_outer_spaces(client_and_engine) -> None:
    client, _ = client_and_engine
    first = signup(client, nickname="  Climber01  ")
    second = signup(client, email="another@example.com", nickname="CLimber01")

    assert first.status_code == second.status_code == 201
    assert first.json()["nickname"] == "Climber01"
    assert second.json()["nickname"] == "CLimber01"


@pytest.mark.parametrize(
    "nickname",
    ["climber01", "CLIMBER01", "12345", "Ab 123", "Ab한글1", "Ab!cd1", "Ab1", "Abcdefghijklmno1", "Ab😀cd1", "AbcD\n1", "\tAbcd1"],
)
def test_signup_rejects_invalid_nickname(client_and_engine, nickname: str) -> None:
    client, _ = client_and_engine

    response = signup(client, nickname=nickname)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "nickname"]


def test_signup_race_returns_nickname_conflict(client_and_engine, monkeypatch) -> None:
    client, engine = client_and_engine
    assert signup(client).status_code == 201
    original_scalar = Session.scalar

    def miss_precheck(self, statement, *args, **kwargs):
        if "nickname" in str(statement.whereclause):
            return None
        return original_scalar(self, statement, *args, **kwargs)

    monkeypatch.setattr(Session, "scalar", miss_precheck)
    response = signup(client, email="another@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "Nickname is already taken"
    with Session(engine) as db:
        assert db.scalar(select(User).where(User.email == "another@example.com")) is None


def test_signup_race_returns_email_conflict(client_and_engine, monkeypatch) -> None:
    client, _ = client_and_engine
    assert signup(client).status_code == 201
    original_scalar = Session.scalar

    def miss_precheck(self, statement, *args, **kwargs):
        if "email" in str(statement.whereclause):
            return None
        return original_scalar(self, statement, *args, **kwargs)

    monkeypatch.setattr(Session, "scalar", miss_precheck)
    response = signup(client, nickname="OtherAa")

    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


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
    assert response.json() == {"id": 1, "email": "user@example.com", "nickname": "Climber01"}


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
