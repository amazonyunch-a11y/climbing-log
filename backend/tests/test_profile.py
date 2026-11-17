from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user_profile import UserProfile
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


def signup(client: TestClient, email: str, nickname: str) -> int:
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "correct-password",
            "nickname": nickname,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    mark_email_verified(email)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_signup_creates_an_empty_user_profile(client_and_engine) -> None:
    client, engine = client_and_engine
    user_id = signup(client, "user@example.com", "Climber01")

    with Session(engine) as db:
        profiles = db.scalars(
            select(UserProfile).where(UserProfile.userId == user_id)
        ).all()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.createdAt is not None
    assert profile.updatedAt is not None
    assert profile.birthDate is None
    assert profile.heightCm is None
    assert profile.weightKg is None
    assert profile.armLengthCm is None


def test_get_profile_returns_only_the_authenticated_users_profile(client_and_engine) -> None:
    client, _ = client_and_engine
    first_user_id = signup(client, "first@example.com", "FirstAa")
    second_user_id = signup(client, "second@example.com", "SecondAa")
    first_headers = auth_headers(client, "first@example.com")
    second_headers = auth_headers(client, "second@example.com")
    assert (
        client.patch("/api/profile", headers=first_headers, json={"height_cm": 165}).status_code
        == 200
    )

    response = client.get("/api/profile", headers=second_headers)

    assert response.status_code == 200
    assert response.json() == {
        "user_id": second_user_id,
        "nickname": "SecondAa",
        "birth_date": None,
        "height_cm": None,
        "weight_kg": None,
        "arm_length_cm": None,
    }
    assert response.json()["user_id"] != first_user_id


def test_profile_rejects_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.get("/api/profile").status_code == 401
    assert client.patch("/api/profile", json={"height_cm": 165}).status_code == 401


def test_profile_changes_nickname_and_keeps_other_fields(client_and_engine) -> None:
    client, _ = client_and_engine
    signup(client, "user@example.com", "Climber01")
    headers = auth_headers(client, "user@example.com")
    assert client.patch("/api/profile", headers=headers, json={"height_cm": 165}).status_code == 200

    response = client.patch("/api/profile", headers=headers, json={"nickname": "  NewName1  "})

    assert response.status_code == 200
    assert response.json()["nickname"] == "NewName1"
    assert response.json()["height_cm"] == 165
    assert client.get("/api/auth/me", headers=headers).json()["nickname"] == "NewName1"


def test_profile_rejects_another_users_nickname(client_and_engine) -> None:
    client, _ = client_and_engine
    signup(client, "first@example.com", "FirstAa")
    signup(client, "second@example.com", "SecondAa")
    headers = auth_headers(client, "first@example.com")

    response = client.patch("/api/profile", headers=headers, json={"nickname": "SecondAa"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Nickname is already taken"
    assert client.get("/api/profile", headers=headers).json()["nickname"] == "FirstAa"


def test_profile_accepts_own_nickname(client_and_engine) -> None:
    client, _ = client_and_engine
    signup(client, "user@example.com", "Climber01")
    headers = auth_headers(client, "user@example.com")

    response = client.patch("/api/profile", headers=headers, json={"nickname": "Climber01"})

    assert response.status_code == 200
    assert response.json()["nickname"] == "Climber01"


@pytest.mark.parametrize("nickname", [None, "", "climber01", "CLIMBER01", "Ab 123", "Ab!cd1"])
def test_profile_rejects_invalid_nickname(client_and_engine, nickname) -> None:
    client, _ = client_and_engine
    signup(client, "user@example.com", "Climber01")
    headers = auth_headers(client, "user@example.com")

    response = client.patch("/api/profile", headers=headers, json={"nickname": nickname})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "nickname"]


def test_profile_race_returns_nickname_conflict(client_and_engine, monkeypatch) -> None:
    client, engine = client_and_engine
    signup(client, "first@example.com", "FirstAa")
    signup(client, "second@example.com", "SecondAa")
    headers = auth_headers(client, "first@example.com")
    original_scalar = Session.scalar

    def miss_precheck(self, statement, *args, **kwargs):
        if "nickname" in str(statement.whereclause):
            return None
        return original_scalar(self, statement, *args, **kwargs)

    monkeypatch.setattr(Session, "scalar", miss_precheck)
    response = client.patch("/api/profile", headers=headers, json={"nickname": "SecondAa"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Nickname is already taken"
    with Session(engine) as db:
        assert db.scalar(select(User).where(User.email == "first@example.com")).nickname == "FirstAa"


def test_patch_profile_updates_only_provided_fields_and_updates_timestamp(client_and_engine) -> None:
    client, engine = client_and_engine
    user_id = signup(client, "user@example.com", "Climber01")
    headers = auth_headers(client, "user@example.com")
    with Session(engine) as db:
        before = db.scalar(select(UserProfile).where(UserProfile.userId == user_id))
        assert before is not None
        initial_update_at = before.updatedAt

    response = client.patch(
        "/api/profile",
        headers=headers,
        json={
            "birth_date": "2001-01-01",
            "height_cm": 165,
            "weight_kg": 55,
            "arm_length_cm": 70,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": user_id,
        "nickname": "Climber01",
        "birth_date": "2001-01-01",
        "height_cm": 165,
        "weight_kg": 55,
        "arm_length_cm": 70,
    }

    response = client.patch("/api/profile", headers=headers, json={"height_cm": 166})
    assert response.status_code == 200
    assert response.json()["height_cm"] == 166
    assert response.json()["weight_kg"] == 55
    assert response.json()["arm_length_cm"] == 70

    with Session(engine) as db:
        profile = db.scalar(select(UserProfile).where(UserProfile.userId == user_id))
        assert profile is not None
        assert profile.birthDate == datetime(2001, 1, 1)
        assert profile.updatedAt != initial_update_at


@pytest.mark.parametrize("method", ["get", "patch"])
def test_profile_creates_a_missing_legacy_profile(client_and_engine, method: str) -> None:
    client, engine = client_and_engine
    user_id = signup(client, "legacy@example.com", "LegacyAa")
    headers = auth_headers(client, "legacy@example.com")
    with Session(engine) as db:
        profile = db.scalar(select(UserProfile).where(UserProfile.userId == user_id))
        assert profile is not None
        db.delete(profile)
        db.commit()

    if method == "get":
        response = client.get("/api/profile", headers=headers)
    else:
        response = client.patch("/api/profile", headers=headers, json={"weight_kg": 55})

    assert response.status_code == 200
    with Session(engine) as db:
        profiles = db.scalars(
            select(UserProfile).where(UserProfile.userId == user_id)
        ).all()

    assert len(profiles) == 1
    assert profiles[0].createdAt is not None
    if method == "patch":
        assert response.json()["weight_kg"] == 55
