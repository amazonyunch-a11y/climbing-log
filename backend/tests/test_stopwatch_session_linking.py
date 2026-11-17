from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.stopwatch_session import StopwatchSession
from tests.test_grade_logs import client_and_engine, signup_and_headers


def create_gym(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/gyms", headers=headers, json={"name": "짐", "location": "서울"}
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_session(
    client: TestClient,
    headers: dict[str, str],
    gym_id: int,
    date: str,
    **overrides,
):
    payload = {
        "gym_id": gym_id,
        "session_date": date,
        "started_at": f"{date}T09:00:00+09:00",
        "ended_at": f"{date}T10:00:00+09:00",
    }
    payload.update(overrides)
    response = client.post(
        "/api/sessions",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    return response


def start_and_finish(client, headers, monkeypatch, start: datetime, end: datetime):
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: start)
    stopwatch_id = client.post("/api/stopwatch", headers=headers).json()["id"]
    monkeypatch.setattr("app.api.stopwatch.utc_now", lambda: end)
    return client.patch(f"/api/stopwatch/{stopwatch_id}/finish", headers=headers)


def test_pending_stopwatches_returns_empty_list(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")

    response = client.get(
        "/api/stopwatch/pending",
        headers=headers,
        params={"session_date": "2026-10-23"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_finish_links_exactly_one_same_kst_date_session(client_and_engine, monkeypatch) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    session = create_session(client, headers, create_gym(client, headers), "2026-10-23")
    start = datetime(2026, 10, 22, 15, 30)  # 2026-10-23 00:30 KST
    finished = start_and_finish(client, headers, monkeypatch, start, start + timedelta(seconds=3661))

    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"
    assert finished.json()["linkedSessionId"] == session.json()["id"]
    assert finished.json()["sessionLinkStatus"] == "linked"
    detail = client.get(f"/api/sessions/{session.json()['id']}", headers=headers).json()
    assert detail["duration_source"] == "stopwatch"
    assert detail["stopwatch_id"] == finished.json()["id"]
    assert detail["duration_minutes"] == 61
    calendar = client.get("/api/calendar/2026-10-23", headers=headers)
    assert calendar.json()["sessions"][0]["duration_minutes"] == 61
    statistics = client.get(
        "/api/statistics/summary",
        headers=headers,
        params={"period": "monthly", "year": 2026, "month": 10},
    )
    assert statistics.json()["total_duration_minutes"] == 61


def test_finish_without_session_is_pending_then_session_creation_links(client_and_engine, monkeypatch) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    start = datetime(2026, 10, 22, 15, 0)
    finished = start_and_finish(client, headers, monkeypatch, start, start + timedelta(minutes=30))

    assert finished.json()["sessionLinkStatus"] == "pending"
    pending = client.get(
        "/api/stopwatch/pending", headers=headers, params={"session_date": "2026-10-23"}
    )
    assert [item["id"] for item in pending.json()] == [finished.json()["id"]]
    session = create_session(client, headers, create_gym(client, headers), "2026-10-23")
    assert session.json()["duration_source"] == "stopwatch"
    assert session.json()["stopwatch_id"] == finished.json()["id"]


def test_session_creation_does_not_choose_between_two_pending_stopwatches(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    first = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 15, 0),
        datetime(2026, 10, 22, 15, 10),
    )
    second = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 16, 0),
        datetime(2026, 10, 22, 16, 10),
    )

    session = create_session(
        client, headers, create_gym(client, headers), "2026-10-23"
    )

    assert session.json()["duration_source"] == "manual"
    assert session.json()["stopwatch_id"] is None
    pending = client.get(
        "/api/stopwatch/pending",
        headers=headers,
        params={"session_date": "2026-10-23"},
    )
    assert [item["id"] for item in pending.json()] == [
        first.json()["id"],
        second.json()["id"],
    ]


def test_session_creation_links_selected_stopwatch_among_multiple_pending(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    first = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 15, 0),
        datetime(2026, 10, 22, 15, 10),
    ).json()
    second = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 16, 0),
        datetime(2026, 10, 22, 16, 10),
    ).json()

    session = create_session(
        client,
        headers,
        create_gym(client, headers),
        "2026-10-23",
        started_at=second["startedAt"],
        ended_at=second["endedAt"],
        stopwatch_id=second["id"],
    )

    assert session.json()["duration_source"] == "stopwatch"
    assert session.json()["stopwatch_id"] == second["id"]
    assert session.json()["started_at"] == second["startedAt"]
    assert session.json()["ended_at"] == second["endedAt"]
    pending = client.get(
        "/api/stopwatch/pending",
        headers=headers,
        params={"session_date": "2026-10-23"},
    )
    assert [item["id"] for item in pending.json()] == [first["id"]]


def test_explicit_null_stopwatch_id_keeps_single_pending_unlinked(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    finished = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 15),
        datetime(2026, 10, 22, 16),
    ).json()

    session = create_session(
        client,
        headers,
        create_gym(client, headers),
        "2026-10-23",
        stopwatch_id=None,
    )

    assert session.json()["duration_source"] == "manual"
    assert session.json()["stopwatch_id"] is None
    pending = client.get(
        "/api/stopwatch/pending",
        headers=headers,
        params={"session_date": "2026-10-23"},
    )
    assert [item["id"] for item in pending.json()] == [finished["id"]]


def test_selected_stopwatch_keeps_link_but_uses_manually_edited_times(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    finished = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 15),
        datetime(2026, 10, 22, 15, 10),
    ).json()

    session = create_session(
        client,
        headers,
        create_gym(client, headers),
        "2026-10-23",
        started_at="2026-10-23T00:02:00+09:00",
        ended_at="2026-10-23T00:12:00+09:00",
        stopwatch_id=finished["id"],
    )

    assert session.json()["duration_source"] == "manual"
    assert session.json()["stopwatch_id"] == finished["id"]
    assert session.json()["started_at"] == "2026-10-22T15:02:00Z"
    assert session.json()["ended_at"] == "2026-10-22T15:12:00Z"
    assert client.get(
        "/api/stopwatch/pending",
        headers=headers,
        params={"session_date": "2026-10-23"},
    ).json() == []


def test_session_creation_rejects_other_users_stopwatch(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "OwnerAa")
    other_headers = signup_and_headers(client, "other@example.com", "OtherAa")
    finished = start_and_finish(
        client,
        owner_headers,
        monkeypatch,
        datetime(2026, 10, 22, 15),
        datetime(2026, 10, 22, 16),
    ).json()

    response = client.post(
        "/api/sessions",
        headers=other_headers,
        json={
            "gym_id": create_gym(client, other_headers),
            "session_date": "2026-10-23",
            "started_at": finished["startedAt"],
            "ended_at": finished["endedAt"],
            "stopwatch_id": finished["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Stopwatch not found"


def test_session_creation_rejects_in_progress_stopwatch(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    monkeypatch.setattr(
        "app.api.stopwatch.utc_now", lambda: datetime(2026, 10, 22, 15)
    )
    stopwatch = client.post("/api/stopwatch", headers=headers).json()

    response = client.post(
        "/api/sessions",
        headers=headers,
        json={
            "gym_id": create_gym(client, headers),
            "session_date": "2026-10-23",
            "started_at": stopwatch["startedAt"],
            "ended_at": None,
            "stopwatch_id": stopwatch["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Stopwatch is not completed"


def test_session_creation_rejects_already_linked_stopwatch(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    gym_id = create_gym(client, headers)
    finished = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 15),
        datetime(2026, 10, 22, 16),
    ).json()
    create_session(
        client,
        headers,
        gym_id,
        "2026-10-23",
        started_at=finished["startedAt"],
        ended_at=finished["endedAt"],
        stopwatch_id=finished["id"],
    )

    response = client.post(
        "/api/sessions",
        headers=headers,
        json={
            "gym_id": gym_id,
            "session_date": "2026-10-23",
            "started_at": finished["startedAt"],
            "ended_at": finished["endedAt"],
            "stopwatch_id": finished["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Stopwatch is already linked"


def test_session_creation_rejects_stopwatch_from_different_kst_date(
    client_and_engine, monkeypatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    finished = start_and_finish(
        client,
        headers,
        monkeypatch,
        datetime(2026, 10, 22, 15),
        datetime(2026, 10, 22, 16),
    ).json()

    response = client.post(
        "/api/sessions",
        headers=headers,
        json={
            "gym_id": create_gym(client, headers),
            "session_date": "2026-10-24",
            "started_at": "2026-10-24T09:00:00+09:00",
            "ended_at": "2026-10-24T10:00:00+09:00",
            "stopwatch_id": finished["id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Stopwatch must be on session_date in Asia/Seoul"
    )


def test_ambiguous_sessions_do_not_auto_link(client_and_engine, monkeypatch) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    gym_id = create_gym(client, headers)
    create_session(client, headers, gym_id, "2026-10-23")
    create_session(client, headers, gym_id, "2026-10-23")

    response = start_and_finish(
        client, headers, monkeypatch, datetime(2026, 10, 22, 15), datetime(2026, 10, 22, 16)
    )
    assert response.json()["linkedSessionId"] is None
    assert response.json()["sessionLinkStatus"] == "ambiguous"


def test_manual_session_edit_preserves_link_and_prevents_overwrite(client_and_engine, monkeypatch) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    session = create_session(client, headers, create_gym(client, headers), "2026-10-23")
    finished = start_and_finish(
        client, headers, monkeypatch, datetime(2026, 10, 22, 15), datetime(2026, 10, 22, 16)
    )
    updated = client.patch(
        f"/api/sessions/{session.json()['id']}",
        headers=headers,
        json={"ended_at": "2026-10-23T12:00:00+09:00"},
    )
    assert updated.json()["duration_source"] == "manual"
    assert updated.json()["stopwatch_id"] == finished.json()["id"]


def test_session_delete_preserves_stopwatch_metadata(client_and_engine, monkeypatch) -> None:
    client, engine = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "ClimberAa")
    session = create_session(client, headers, create_gym(client, headers), "2026-10-23")
    finished = start_and_finish(
        client, headers, monkeypatch, datetime(2026, 10, 22, 15), datetime(2026, 10, 22, 16)
    )
    assert client.delete(f"/api/sessions/{session.json()['id']}", headers=headers).status_code == 204
    with Session(engine) as db:
        stopwatch = db.scalar(select(StopwatchSession).where(StopwatchSession.id == finished.json()["id"]))
        assert stopwatch is not None
        assert stopwatch.climbingSessionId is None
