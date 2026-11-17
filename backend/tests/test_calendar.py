import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
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


def create_gym(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/gyms",
        headers=headers,
        json={"name": "클라이밍짐", "location": "서울 마포구"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_session(
    client: TestClient,
    headers: dict[str, str],
    gym_id: int,
    session_date: str,
    started_at: str,
    ended_at: str | None = None,
) -> int:
    kst_started_at = started_at[:-1] + "+09:00" if started_at.endswith("Z") else started_at
    kst_ended_at = (
        ended_at[:-1] + "+09:00" if ended_at is not None and ended_at.endswith("Z") else ended_at
    )
    response = client.post(
        "/api/sessions",
        headers=headers,
        json={
            "gym_id": gym_id,
            "session_date": session_date,
            "started_at": kst_started_at,
            "ended_at": kst_ended_at,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_grade_log(
    client: TestClient,
    headers: dict[str, str],
    session_id: int,
    grade_label: str,
    attempts: int,
    sends: int,
) -> None:
    response = client.post(
        f"/api/sessions/{session_id}/grades",
        headers=headers,
        json={
            "grade_label": grade_label,
            "attempts": attempts,
            "sends": sends,
        },
    )
    assert response.status_code == 201


def test_calendar_rejects_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.get("/api/calendar", params={"year": 2026, "month": 9}).status_code == 401
    assert client.get("/api/calendar/2026-09-11").status_code == 401


def test_monthly_calendar_counts_own_sessions_by_date_in_order(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    other_headers = signup_and_headers(client, "other@example.com", "OtherAa")
    gym_id = create_gym(client, headers)
    other_gym_id = create_gym(client, other_headers)
    create_session(client, headers, gym_id, "2026-09-06", "2026-09-06T18:00:00Z")
    create_session(client, headers, gym_id, "2026-09-03", "2026-09-03T18:00:00Z")
    create_session(client, headers, gym_id, "2026-09-03", "2026-09-03T20:00:00Z")
    create_session(client, other_headers, other_gym_id, "2026-09-03", "2026-09-03T18:00:00Z")

    response = client.get("/api/calendar", headers=headers, params={"year": 2026, "month": 9})

    assert response.status_code == 200
    assert response.json() == [
        {"date": "2026-09-03", "session_count": 2},
        {"date": "2026-09-06", "session_count": 1},
    ]


def test_daily_calendar_aggregates_grade_logs_and_keeps_empty_grade_logs_zero(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    gym_id = create_gym(client, headers)
    first_id = create_session(
        client, headers, gym_id, "2026-09-11", "2026-09-11T18:00:00Z", "2026-09-11T19:30:00Z"
    )
    second_id = create_session(
        client, headers, gym_id, "2026-09-11", "2026-09-11T20:00:00Z"
    )
    create_grade_log(client, headers, first_id, "V2", 5, 4)
    create_grade_log(client, headers, first_id, "V3", 2, 1)

    response = client.get("/api/calendar/2026-09-11", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-09-11",
        "sessions": [
            {
                "id": first_id,
                "gym_name": "클라이밍짐",
                "duration_minutes": 90,
                "total_attempts": 7,
                "total_sends": 5,
            },
            {
                "id": second_id,
                "gym_name": "클라이밍짐",
                "duration_minutes": None,
                "total_attempts": 0,
                "total_sends": 0,
            },
        ],
    }


@pytest.mark.parametrize(
    ("requested_date", "next_date"),
    [
        ("2026-10-02", "2026-10-05"),
        ("2026-10-31", "2026-11-01"),
        ("2026-12-31", "2027-01-01"),
    ],
)
def test_daily_calendar_returns_only_requested_date_sessions(
    client_and_engine, requested_date: str, next_date: str
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    gym_id = create_gym(client, headers)
    requested_id = create_session(
        client, headers, gym_id, requested_date, f"{requested_date}T18:00:00Z"
    )
    next_id = create_session(
        client, headers, gym_id, next_date, f"{next_date}T18:00:00Z"
    )

    requested = client.get(f"/api/calendar/{requested_date}", headers=headers)
    following = client.get(f"/api/calendar/{next_date}", headers=headers)

    assert requested.status_code == 200
    assert [session["id"] for session in requested.json()["sessions"]] == [requested_id]
    assert following.status_code == 200
    assert [session["id"] for session in following.json()["sessions"]] == [next_id]


def test_calendar_returns_empty_results_and_excludes_other_users_sessions(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    other_headers = signup_and_headers(client, "other@example.com", "OtherAa")
    other_gym_id = create_gym(client, other_headers)
    create_session(
        client, other_headers, other_gym_id, "2026-10-01", "2026-10-01T18:00:00Z"
    )

    monthly = client.get("/api/calendar", headers=headers, params={"year": 2026, "month": 10})
    daily = client.get("/api/calendar/2026-10-01", headers=headers)
    empty_month = client.get("/api/calendar", headers=headers, params={"year": 2026, "month": 11})

    assert monthly.status_code == 200
    assert monthly.json() == []
    assert daily.status_code == 200
    assert daily.json() == {"date": "2026-10-01", "sessions": []}
    assert empty_month.status_code == 200
    assert empty_month.json() == []


def test_calendar_uses_kst_session_date_when_utc_date_is_previous_day(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")
    gym_id = create_gym(client, headers)

    session_id = create_session(
        client,
        headers,
        gym_id,
        "2026-10-04",
        "2026-10-04T00:30:00+09:00",
    )

    selected_day = client.get("/api/calendar/2026-10-04", headers=headers)
    utc_day = client.get("/api/calendar/2026-10-03", headers=headers)
    assert [session["id"] for session in selected_day.json()["sessions"]] == [session_id]
    assert utc_day.json()["sessions"] == []


@pytest.mark.parametrize("month", [0, 13])
def test_calendar_rejects_out_of_range_month(client_and_engine, month: int) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")

    response = client.get("/api/calendar", headers=headers, params={"year": 2026, "month": month})

    assert response.status_code == 422


def test_calendar_rejects_invalid_date(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "Climber01")

    response = client.get("/api/calendar/not-a-date", headers=headers)

    assert response.status_code == 422
