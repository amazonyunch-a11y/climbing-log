from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.climbing_session import ClimbingSession


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


def create_gym(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/gyms",
        headers=headers,
        json={"name": "클라이밍짐", "location": "서울 마포구"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_session(client: TestClient, headers: dict[str, str], gym_id: int, **overrides):
    payload = {
        "gym_id": gym_id,
        "session_date": "2026-09-11",
        "started_at": "2026-09-11T18:00:00+09:00",
        "ended_at": "2026-09-11T19:30:00+09:00",
        "total_attempts": 15,
        "total_sends": 8,
        "notes": "오버행 위주",
    }
    payload.update(overrides)
    return client.post("/api/sessions", headers=headers, json=payload)


def test_sessions_reject_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.get("/api/sessions").status_code == 401
    assert client.post("/api/sessions", json={}).status_code == 401
    assert client.get("/api/sessions/1").status_code == 401
    assert client.patch("/api/sessions/1", json={}).status_code == 401
    assert client.delete("/api/sessions/1").status_code == 401


def test_create_list_and_get_session(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)

    created = create_session(client, headers, gym_id)

    assert created.status_code == 201
    assert created.json() == {
        "id": 1,
        "gym_id": gym_id,
        "session_date": "2026-09-11",
        "started_at": "2026-09-11T09:00:00Z",
        "ended_at": "2026-09-11T10:30:00Z",
        "duration_minutes": 90,
        "total_attempts": 0,
        "total_sends": 0,
        "notes": "오버행 위주",
    }

    listed = client.get("/api/sessions", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == [
        {
            **created.json(),
            "gym_name": "클라이밍짐",
        }
    ]

    detail = client.get("/api/sessions/1", headers=headers)
    assert detail.status_code == 200
    assert detail.json() == listed.json()[0]


def test_session_without_end_time_is_in_progress(client_and_engine) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)

    response = create_session(client, headers, gym_id, ended_at=None)

    assert response.status_code == 201
    assert response.json()["ended_at"] is None
    assert response.json()["duration_minutes"] is None
    with Session(engine) as db:
        climbing_session = db.get(ClimbingSession, response.json()["id"])
        assert climbing_session is not None
        assert climbing_session.durationMintes is None


def test_patch_session_recalculates_duration_and_preserves_unset_fields(client_and_engine) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)
    session_id = create_session(client, headers, gym_id).json()["id"]

    response = client.patch(
        f"/api/sessions/{session_id}",
        headers=headers,
        json={"ended_at": "2026-09-11T20:00:00+09:00", "notes": "수정 메모"},
    )

    assert response.status_code == 200
    detail = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert response.json() == detail.json()
    assert detail.status_code == 200
    assert detail.json()["duration_minutes"] == 120
    assert detail.json()["total_attempts"] == 0
    assert detail.json()["total_sends"] == 0
    assert detail.json()["notes"] == "수정 메모"
    with Session(engine) as db:
        climbing_session = db.get(ClimbingSession, session_id)
        assert climbing_session is not None
        assert climbing_session.endedAt == datetime(2026, 9, 11, 11, 0)


def test_delete_session_and_then_get_not_found(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)
    session_id = create_session(client, headers, gym_id).json()["id"]

    response = client.delete(f"/api/sessions/{session_id}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/sessions/{session_id}", headers=headers).status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_other_users_session_is_not_exposed(client_and_engine, method: str) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    gym_id = create_gym(client, owner_headers)
    session_id = create_session(client, owner_headers, gym_id).json()["id"]

    if method == "get":
        response = client.get(f"/api/sessions/{session_id}", headers=other_headers)
    elif method == "patch":
        response = client.patch(
            f"/api/sessions/{session_id}",
            headers=other_headers,
            json={"notes": "침해"},
        )
    else:
        response = client.delete(f"/api/sessions/{session_id}", headers=other_headers)

    assert response.status_code == 404


@pytest.mark.parametrize("gym_id_kind", ["missing", "other_user"])
def test_create_session_requires_current_users_gym(client_and_engine, gym_id_kind: str) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    owner_gym_id = create_gym(client, owner_headers)
    gym_id = 999 if gym_id_kind == "missing" else owner_gym_id

    response = create_session(client, other_headers, gym_id)

    assert response.status_code == 404


def test_session_rejects_end_before_start(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)

    response = create_session(
        client,
        headers,
        gym_id,
        started_at="2026-09-11T19:30:00+09:00",
        ended_at="2026-09-11T18:00:00+09:00",
    )

    assert response.status_code == 422


def test_session_converts_kst_input_to_utc_and_keeps_kst_session_date(client_and_engine) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)

    response = create_session(
        client,
        headers,
        gym_id,
        session_date="2026-09-11",
        started_at="2026-09-11T00:30:00+09:00",
        ended_at="2026-09-11T01:15:00+09:00",
    )

    assert response.status_code == 201
    assert response.json()["session_date"] == "2026-09-11"
    assert response.json()["started_at"] == "2026-09-10T15:30:00Z"
    assert response.json()["ended_at"] == "2026-09-10T16:15:00Z"
    with Session(engine) as db:
        climbing_session = db.get(ClimbingSession, response.json()["id"])
        assert climbing_session is not None
        assert climbing_session.sessionDate == datetime(2026, 9, 11)
        assert climbing_session.startedAt == datetime(2026, 9, 10, 15, 30)
        assert climbing_session.endedAt == datetime(2026, 9, 10, 16, 15)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("started_at", "2026-09-12T00:30:00+09:00"),
        ("ended_at", "2026-09-12T00:30:00+09:00"),
    ],
)
def test_session_rejects_kst_time_outside_session_date(client_and_engine, field: str, value: str) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)
    payload = {
        "gym_id": gym_id,
        "session_date": "2026-09-11",
        "started_at": "2026-09-11T18:00:00+09:00",
        "ended_at": "2026-09-11T19:30:00+09:00",
    }
    payload[field] = value

    response = client.post("/api/sessions", headers=headers, json=payload)

    assert response.status_code == 422


def test_session_update_rejects_kst_time_outside_session_date_and_allows_null_end_time(
    client_and_engine,
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)
    session_id = create_session(client, headers, gym_id).json()["id"]

    rejected = client.patch(
        f"/api/sessions/{session_id}",
        headers=headers,
        json={"started_at": "2026-09-12T00:30:00+09:00"},
    )
    cleared = client.patch(
        f"/api/sessions/{session_id}",
        headers=headers,
        json={"ended_at": None},
    )

    assert rejected.status_code == 422
    assert cleared.status_code == 200
    assert cleared.json()["ended_at"] is None
    assert cleared.json()["duration_minutes"] is None


def test_session_totals_are_derived_from_grade_logs(client_and_engine) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    gym_id = create_gym(client, headers)
    session_id = create_session(client, headers, gym_id).json()["id"]

    assert client.post(
        f"/api/sessions/{session_id}/grades",
        headers=headers,
        json={"grade_label": "V2", "attempts": 5, "sends": 3},
    ).status_code == 201
    second_grade = client.post(
        f"/api/sessions/{session_id}/grades",
        headers=headers,
        json={"grade_label": "V3", "attempts": 4, "sends": 2},
    )
    assert second_grade.status_code == 201

    detail = client.get(f"/api/sessions/{session_id}", headers=headers)
    listed = client.get("/api/sessions", headers=headers)
    assert detail.json()["total_attempts"] == 9
    assert detail.json()["total_sends"] == 5
    assert listed.json()[0]["total_attempts"] == 9
    assert listed.json()[0]["total_sends"] == 5
    with Session(engine) as db:
        climbing_session = db.get(ClimbingSession, session_id)
        assert climbing_session is not None
        assert climbing_session.totalAteempts is None
        assert climbing_session.totalSends is None

    updated = client.patch(
        f"/api/grades/{second_grade.json()['id']}",
        headers=headers,
        json={"attempts": 6, "sends": 4},
    )
    assert updated.status_code == 200
    assert client.get(f"/api/sessions/{session_id}", headers=headers).json()[
        "total_attempts"
    ] == 11
    assert client.get(f"/api/sessions/{session_id}", headers=headers).json()[
        "total_sends"
    ] == 7

    deleted = client.delete(f"/api/grades/{second_grade.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/sessions/{session_id}", headers=headers).json()[
        "total_attempts"
    ] == 5
    assert client.get(f"/api/sessions/{session_id}", headers=headers).json()[
        "total_sends"
    ] == 3
