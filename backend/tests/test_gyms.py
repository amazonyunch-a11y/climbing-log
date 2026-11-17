from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.gyms import Gyms
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


def signup_and_headers(client: TestClient, email: str, nickname: str) -> dict[str, str]:
    signup = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "correct-password", "nickname": nickname},
    )
    assert signup.status_code == 201
    mark_email_verified(email)
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_gym(client: TestClient, headers: dict[str, str], name: str = "클라이밍짐"):
    return client.post(
        "/api/gyms",
        headers=headers,
        json={"name": name, "location": "서울 마포구"},
    )


def test_list_gyms_returns_only_current_users_gyms(client_and_engine) -> None:
    client, _ = client_and_engine
    first_headers = signup_and_headers(client, "first@example.com", "FirstAa")
    second_headers = signup_and_headers(client, "second@example.com", "SecondAa")
    assert create_gym(client, first_headers).status_code == 201

    first_response = client.get("/api/gyms", headers=first_headers)
    second_response = client.get("/api/gyms", headers=second_headers)

    assert first_response.status_code == 200
    assert first_response.json() == [
        {"id": 1, "name": "클라이밍짐", "location": "서울 마포구"}
    ]
    assert second_response.status_code == 200
    assert second_response.json() == []


def test_create_and_get_gym(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")

    created = create_gym(client, headers)

    assert created.status_code == 201
    assert set(created.json()) == {"id", "name", "location", "created_at"}
    assert created.json()["created_at"].endswith("Z")
    gym_id = created.json()["id"]

    detail = client.get(f"/api/gyms/{gym_id}", headers=headers)

    assert detail.status_code == 200
    assert detail.json() == {
        "id": gym_id,
        "name": "클라이밍짐",
        "location": "서울 마포구",
    }


def test_patch_gym_updates_only_supplied_fields_and_timestamp(client_and_engine) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    gym_id = create_gym(client, headers).json()["id"]
    with Session(engine) as db:
        gym = db.get(Gyms, gym_id)
        assert gym is not None
        initial_update_at = gym.updateAt

    response = client.patch(
        f"/api/gyms/{gym_id}",
        headers=headers,
        json={"location": "서울 강남구"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": gym_id,
        "name": "클라이밍짐",
        "location": "서울 강남구",
    }
    with Session(engine) as db:
        gym = db.get(Gyms, gym_id)
        assert gym is not None
        assert gym.name == "클라이밍짐"
        assert gym.lacation == "서울 강남구"
        assert isinstance(gym.updateAt, datetime)
        assert gym.updateAt != initial_update_at


def test_delete_gym(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    gym_id = create_gym(client, headers).json()["id"]

    response = client.delete(f"/api/gyms/{gym_id}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/gyms/{gym_id}", headers=headers).status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_gym_returns_not_found(client_and_engine, method: str) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")

    if method == "get":
        response = client.get("/api/gyms/999", headers=headers)
    elif method == "patch":
        response = client.patch("/api/gyms/999", headers=headers, json={"name": "변경"})
    else:
        response = client.delete("/api/gyms/999", headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_other_users_gym_returns_not_found(client_and_engine, method: str) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "OwnerAa")
    other_headers = signup_and_headers(client, "other@example.com", "OtherAa")
    gym_id = create_gym(client, owner_headers).json()["id"]

    if method == "get":
        response = client.get(f"/api/gyms/{gym_id}", headers=other_headers)
    elif method == "patch":
        response = client.patch(
            f"/api/gyms/{gym_id}", headers=other_headers, json={"name": "변경"}
        )
    else:
        response = client.delete(f"/api/gyms/{gym_id}", headers=other_headers)

    assert response.status_code == 404


def test_gyms_reject_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.get("/api/gyms").status_code == 401
    assert client.post("/api/gyms", json={"name": "암장", "location": "서울"}).status_code == 401
    assert client.get("/api/gyms/1").status_code == 401
    assert client.patch("/api/gyms/1", json={"name": "암장"}).status_code == 401
    assert client.delete("/api/gyms/1").status_code == 401
