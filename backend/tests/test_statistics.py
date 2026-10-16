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


def create_gym(client: TestClient, headers: dict[str, str], name: str) -> int:
    response = client.post(
        "/api/gyms",
        headers=headers,
        json={"name": name, "location": "서울"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_session(
    client: TestClient,
    headers: dict[str, str],
    gym_id: int,
    session_date: str,
    started_at: str,
    ended_at: str | None,
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


def create_statistics_data(client: TestClient, headers: dict[str, str]) -> tuple[int, int]:
    first_gym_id = create_gym(client, headers, "첫 번째 암장")
    second_gym_id = create_gym(client, headers, "두 번째 암장")
    first_session_id = create_session(
        client,
        headers,
        first_gym_id,
        "2026-09-03",
        "2026-09-03T18:00:00Z",
        "2026-09-03T19:00:00Z",
    )
    create_grade_log(client, headers, first_session_id, "V2", 5, 3)
    create_grade_log(client, headers, first_session_id, "V3", 0, 0)
    create_session(
        client,
        headers,
        first_gym_id,
        "2026-09-04",
        "2026-09-04T18:00:00Z",
        None,
    )
    third_session_id = create_session(
        client,
        headers,
        second_gym_id,
        "2026-09-08",
        "2026-09-08T18:00:00Z",
        "2026-09-08T18:30:00Z",
    )
    create_grade_log(client, headers, third_session_id, "V2", 4, 2)
    return first_gym_id, second_gym_id


def test_statistics_reject_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine
    params = {"period": "monthly", "year": 2026, "month": 9}

    assert client.get("/api/statistics/summary", params=params).status_code == 401
    assert client.get("/api/statistics/grades", params=params).status_code == 401
    assert client.get("/api/statistics/gyms", params=params).status_code == 401


def test_summary_monthly_and_weekly_exclude_other_users_data(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    create_statistics_data(client, headers)
    other_gym_id = create_gym(client, other_headers, "다른 사용자 암장")
    other_session_id = create_session(
        client,
        other_headers,
        other_gym_id,
        "2026-09-03",
        "2026-09-03T18:00:00Z",
        "2026-09-03T22:00:00Z",
    )
    create_grade_log(client, other_headers, other_session_id, "V9", 100, 100)

    monthly = client.get(
        "/api/statistics/summary",
        headers=headers,
        params={"period": "monthly", "year": 2026, "month": 9},
    )
    weekly = client.get(
        "/api/statistics/summary",
        headers=headers,
        params={"period": "weekly", "start_date": "2026-09-03"},
    )

    assert monthly.status_code == 200
    assert monthly.json()["period"] == "monthly"
    assert monthly.json()["session_count"] == 3
    assert monthly.json()["total_duration_minutes"] == 90
    assert monthly.json()["total_attempts"] == 9
    assert monthly.json()["total_sends"] == 5
    assert monthly.json()["send_rate"] == pytest.approx(5 / 9 * 100)
    assert weekly.status_code == 200
    assert weekly.json() == {**monthly.json(), "period": "weekly"}


def test_grade_and_gym_statistics_for_monthly_and_weekly_periods(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    first_gym_id, second_gym_id = create_statistics_data(client, headers)
    monthly_params = {"period": "monthly", "year": 2026, "month": 9}
    weekly_params = {"period": "weekly", "start_date": "2026-09-03"}

    grades = client.get("/api/statistics/grades", headers=headers, params=monthly_params)
    weekly_grades = client.get("/api/statistics/grades", headers=headers, params=weekly_params)
    gyms = client.get("/api/statistics/gyms", headers=headers, params=monthly_params)
    weekly_gyms = client.get("/api/statistics/gyms", headers=headers, params=weekly_params)

    assert grades.status_code == 200
    assert grades.json() == [
        {
            "grade_label": "V2",
            "attempts": 9,
            "sends": 5,
            "send_rate": pytest.approx(5 / 9 * 100),
        },
        {"grade_label": "V3", "attempts": 0, "sends": 0, "send_rate": 0.0},
    ]
    assert weekly_grades.status_code == 200
    assert weekly_grades.json() == grades.json()
    assert gyms.status_code == 200
    assert gyms.json() == [
        {"gym_id": first_gym_id, "gym_name": "첫 번째 암장", "visit_count": 2},
        {"gym_id": second_gym_id, "gym_name": "두 번째 암장", "visit_count": 1},
    ]
    assert weekly_gyms.status_code == 200
    assert weekly_gyms.json() == gyms.json()


def test_statistics_return_zero_or_empty_results_for_empty_period(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    params = {"period": "monthly", "year": 2026, "month": 12}

    summary = client.get("/api/statistics/summary", headers=headers, params=params)
    grades = client.get("/api/statistics/grades", headers=headers, params=params)
    gyms = client.get("/api/statistics/gyms", headers=headers, params=params)

    assert summary.status_code == 200
    assert summary.json() == {
        "period": "monthly",
        "session_count": 0,
        "total_duration_minutes": 0,
        "total_attempts": 0,
        "total_sends": 0,
        "send_rate": 0.0,
    }
    assert grades.status_code == 200
    assert grades.json() == []
    assert gyms.status_code == 200
    assert gyms.json() == []


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"period": "daily"},
        {"period": "monthly", "month": 9},
        {"period": "weekly"},
        {"period": "monthly", "year": 2026, "month": 13},
        {"period": "weekly", "start_date": "not-a-date"},
    ],
)
def test_statistics_reject_invalid_period_parameters(client_and_engine, params) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")

    response = client.get("/api/statistics/summary", headers=headers, params=params)

    assert response.status_code == 422
