import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app


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
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-password"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_session(client: TestClient, headers: dict[str, str]) -> int:
    gym = client.post(
        "/api/gyms",
        headers=headers,
        json={"name": "클라이밍짐", "location": "서울 마포구"},
    )
    assert gym.status_code == 201
    session = client.post(
        "/api/sessions",
        headers=headers,
        json={
            "gym_id": gym.json()["id"],
            "session_date": "2026-09-11",
            "started_at": "2026-09-11T18:00:00+09:00",
        },
    )
    assert session.status_code == 201
    return session.json()["id"]


def create_grade_log(
    client: TestClient,
    headers: dict[str, str],
    session_id: int,
    **overrides,
):
    payload = {"grade_label": "V2", "attempts": 5, "sends": 4}
    payload.update(overrides)
    return client.post(
        f"/api/sessions/{session_id}/grades",
        headers=headers,
        json=payload,
    )


def test_grade_logs_reject_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.get("/api/sessions/1/grades").status_code == 401
    assert client.post("/api/sessions/1/grades", json={}).status_code == 401
    assert client.patch("/api/grades/1", json={}).status_code == 401
    assert client.delete("/api/grades/1").status_code == 401


def test_create_list_and_update_grade_log(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)

    created = create_grade_log(client, headers, session_id)
    assert created.status_code == 201
    assert created.json() == {
        "id": 1,
        "session_id": session_id,
        "grade_label": "V2",
        "attempts": 5,
        "sends": 4,
    }

    duplicate = create_grade_log(client, headers, session_id)
    assert duplicate.status_code == 201

    listed = client.get(f"/api/sessions/{session_id}/grades", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == [created.json(), duplicate.json()]

    updated = client.patch(
        "/api/grades/1",
        headers=headers,
        json={"attempts": 6, "sends": 5},
    )
    assert updated.status_code == 200
    assert updated.json() == {
        "id": 1,
        "session_id": session_id,
        "grade_label": "V2",
        "attempts": 6,
        "sends": 5,
    }


def test_delete_grade_log_removes_it_from_session_list(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)
    grade_id = create_grade_log(client, headers, session_id).json()["id"]

    deleted = client.delete(f"/api/grades/{grade_id}", headers=headers)

    assert deleted.status_code == 204
    assert deleted.content == b""
    listed = client.get(f"/api/sessions/{session_id}/grades", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_other_users_session_grade_logs_are_not_exposed_or_created(client_and_engine) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    owner_session_id = create_session(client, owner_headers)

    assert client.get(
        f"/api/sessions/{owner_session_id}/grades", headers=other_headers
    ).status_code == 404
    assert create_grade_log(client, other_headers, owner_session_id).status_code == 404


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_other_users_grade_log_cannot_be_changed(client_and_engine, method: str) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    owner_session_id = create_session(client, owner_headers)
    grade_id = create_grade_log(client, owner_headers, owner_session_id).json()["id"]

    if method == "patch":
        response = client.patch(
            f"/api/grades/{grade_id}",
            headers=other_headers,
            json={"attempts": 6},
        )
    else:
        response = client.delete(f"/api/grades/{grade_id}", headers=other_headers)

    assert response.status_code == 404


def test_missing_session_cannot_receive_grade_log(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")

    assert create_grade_log(client, headers, 999).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"grade_label": "V2", "attempts": -1, "sends": 0},
        {"grade_label": "V2", "attempts": 1, "sends": -1},
        {"grade_label": "V2", "attempts": 1, "sends": 2},
    ],
)
def test_grade_log_rejects_invalid_counts(client_and_engine, payload) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)

    response = client.post(
        f"/api/sessions/{session_id}/grades",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422
