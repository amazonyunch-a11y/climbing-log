from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.stopwatch_session import StopwatchSession
from tests.test_grade_logs import client_and_engine, signup_and_headers


def start_stopwatch(client: TestClient, headers: dict[str, str]):
    return client.post("/api/stopwatch", headers=headers)


def test_stopwatch_routes_require_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.post("/api/stopwatch").status_code == 401
    assert client.get("/api/stopwatch/active").status_code == 401
    assert client.patch("/api/stopwatch/1/stop").status_code == 401
    assert client.patch("/api/stopwatch/1/reset").status_code == 401


def test_start_and_get_active_stopwatch(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")

    started = start_stopwatch(client, headers)

    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "in_progress"
    assert body["startedAt"].endswith("Z")
    assert body["endedAt"] is None
    assert body["elapsedSeconds"] == 0
    assert client.get("/api/stopwatch/active", headers=headers).json() == body


def test_get_active_returns_404_when_no_stopwatch_exists(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")

    response = client.get("/api/stopwatch/active", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No active stopwatch"


def test_start_rejects_second_active_stopwatch(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    assert start_stopwatch(client, headers).status_code == 201

    response = start_stopwatch(client, headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "An active stopwatch already exists"


def test_stop_pauses_and_persists_elapsed_seconds(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    started_at = datetime(2026, 10, 14, 1, 0, 0)
    ended_at = started_at + timedelta(seconds=3723)
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: started_at)
    stopwatch_id = start_stopwatch(client, headers).json()["id"]
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: ended_at)

    stopped = client.patch(f"/api/stopwatch/{stopwatch_id}/stop", headers=headers)

    assert stopped.status_code == 200
    assert stopped.json() == {
        "id": stopwatch_id,
        "status": "paused",
        "startedAt": "2026-10-14T01:00:00Z",
        "endedAt": "2026-10-14T02:02:03Z",
        "elapsedSeconds": 3723,
    }
    assert client.get("/api/stopwatch/active", headers=headers).json() == stopped.json()


def test_start_resumes_paused_stopwatch_and_accumulates_elapsed_seconds(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    started_at = datetime(2026, 10, 14, 1, 0, 0)
    paused_at = started_at + timedelta(seconds=90)
    resumed_at = started_at + timedelta(minutes=10)
    checked_at = resumed_at + timedelta(seconds=45)

    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: started_at)
    stopwatch_id = start_stopwatch(client, headers).json()["id"]
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: paused_at)
    assert client.patch(f"/api/stopwatch/{stopwatch_id}/stop", headers=headers).json()[
        "elapsedSeconds"
    ] == 90

    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: resumed_at)
    resumed = start_stopwatch(client, headers)

    assert resumed.status_code == 201
    assert resumed.json() == {
        "id": stopwatch_id,
        "status": "in_progress",
        "startedAt": "2026-10-14T01:10:00Z",
        "endedAt": None,
        "elapsedSeconds": 90,
    }

    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: checked_at)
    active = client.get("/api/stopwatch/active", headers=headers)
    assert active.status_code == 200
    assert active.json()["elapsedSeconds"] == 135


def test_reset_cancels_and_keeps_elapsed_seconds(
    client_and_engine, monkeypatch
) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    started_at = datetime(2026, 10, 14, 1, 0, 0)
    reset_at = started_at + timedelta(seconds=90)
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: started_at)
    stopwatch_id = start_stopwatch(client, headers).json()["id"]
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: reset_at)

    reset = client.patch(f"/api/stopwatch/{stopwatch_id}/reset", headers=headers)

    assert reset.status_code == 200
    assert reset.json()["status"] == "canceled"
    assert reset.json()["elapsedSeconds"] == 90
    with Session(engine) as db:
        persisted = db.scalar(select(StopwatchSession).where(StopwatchSession.id == stopwatch_id))
        assert persisted is not None
        assert persisted.status == "canceled"
        assert persisted.elapsedSeconds == 90
    assert client.get("/api/stopwatch/active", headers=headers).status_code == 404

    replacement = start_stopwatch(client, headers)
    assert replacement.status_code == 201
    assert replacement.json()["id"] != stopwatch_id
    assert replacement.json()["elapsedSeconds"] == 0


def test_reset_accepts_a_paused_stopwatch(client_and_engine, monkeypatch) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    started_at = datetime(2026, 10, 14, 1, 0, 0)
    paused_at = started_at + timedelta(seconds=60)
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: started_at)
    stopwatch_id = start_stopwatch(client, headers).json()["id"]
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: paused_at)
    assert client.patch(f"/api/stopwatch/{stopwatch_id}/stop", headers=headers).status_code == 200

    reset = client.patch(f"/api/stopwatch/{stopwatch_id}/reset", headers=headers)

    assert reset.status_code == 200
    assert reset.json()["status"] == "canceled"
    assert reset.json()["elapsedSeconds"] == 60


def test_other_user_cannot_stop_stopwatch(client_and_engine) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    stopwatch_id = start_stopwatch(client, owner_headers).json()["id"]

    assert client.patch(f"/api/stopwatch/{stopwatch_id}/stop", headers=other_headers).status_code == 404
    assert client.patch(f"/api/stopwatch/{stopwatch_id}/reset", headers=other_headers).status_code == 404
