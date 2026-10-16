import pytest
from starlette.testclient import TestClient

from app.services.storage import StorageConfigurationError, StorageDeletionError
from tests.test_grade_logs import client_and_engine, create_session, signup_and_headers


def create_video(
    client: TestClient,
    headers: dict[str, str],
    session_id: int,
    storage_path: str = "videos/user-1/session-10/video-001.mp4",
):
    return client.post(
        f"/api/sessions/{session_id}/videos",
        headers=headers,
        json={"storage_path": storage_path},
    )


def test_video_routes_reject_missing_bearer_token(client_and_engine) -> None:
    client, _ = client_and_engine

    assert client.post("/api/sessions/1/videos", json={}).status_code == 401
    assert client.get("/api/sessions/1/videos").status_code == 401
    assert client.delete("/api/videos/1").status_code == 401


def test_create_and_list_videos_includes_public_file_url(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)

    created = create_video(client, headers, session_id)

    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["session_id"] == session_id
    assert body["storage_path"] == "videos/user-1/session-10/video-001.mp4"
    assert body["file_url"] == (
        "https://test-project.supabase.co/storage/v1/object/public/"
        "climbing-videos/videos/user-1/session-10/video-001.mp4"
    )
    assert body["uploaded_at"].endswith("Z")

    listed = client.get(f"/api/sessions/{session_id}/videos", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == [body]


def test_delete_video_removes_storage_file_then_metadata(
    client_and_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)
    storage_path = "videos/user-1/session-10/video-001.mp4"
    video_id = create_video(client, headers, session_id, storage_path).json()["id"]
    deleted_paths: list[str] = []
    monkeypatch.setattr(
        "app.api.videos.delete_storage_object", deleted_paths.append
    )

    deleted = client.delete(f"/api/videos/{video_id}", headers=headers)

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert deleted_paths == [storage_path]
    listed = client.get(f"/api/sessions/{session_id}/videos", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_storage_delete_failure_keeps_video_metadata(
    client_and_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)
    video_id = create_video(client, headers, session_id).json()["id"]

    def fail_delete(_: str) -> None:
        raise StorageDeletionError("Storage unavailable")

    monkeypatch.setattr("app.api.videos.delete_storage_object", fail_delete)

    deleted = client.delete(f"/api/videos/{video_id}", headers=headers)

    assert deleted.status_code == 502
    assert deleted.json()["detail"] == "Video file could not be deleted from storage. Please retry."
    listed = client.get(f"/api/sessions/{session_id}/videos", headers=headers)
    assert [video["id"] for video in listed.json()] == [video_id]


def test_storage_delete_configuration_error_keeps_video_metadata(
    client_and_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)
    video_id = create_video(client, headers, session_id).json()["id"]

    def fail_delete(_: str) -> None:
        raise StorageConfigurationError("SUPABASE_SERVICE_ROLE_KEY is missing")

    monkeypatch.setattr("app.api.videos.delete_storage_object", fail_delete)

    deleted = client.delete(f"/api/videos/{video_id}", headers=headers)

    assert deleted.status_code == 503
    assert deleted.json()["detail"] == "Video storage delete is not configured. Please contact support."
    listed = client.get(f"/api/sessions/{session_id}/videos", headers=headers)
    assert [video["id"] for video in listed.json()] == [video_id]


def test_other_users_session_videos_are_not_exposed_or_created(client_and_engine) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    owner_session_id = create_session(client, owner_headers)

    assert client.get(
        f"/api/sessions/{owner_session_id}/videos", headers=other_headers
    ).status_code == 404
    assert create_video(client, other_headers, owner_session_id).status_code == 404


def test_other_users_video_cannot_be_deleted(
    client_and_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = client_and_engine
    owner_headers = signup_and_headers(client, "owner@example.com", "owner")
    other_headers = signup_and_headers(client, "other@example.com", "other")
    owner_session_id = create_session(client, owner_headers)
    video_id = create_video(client, owner_headers, owner_session_id).json()["id"]
    deleted_paths: list[str] = []
    monkeypatch.setattr(
        "app.api.videos.delete_storage_object", deleted_paths.append
    )

    assert client.delete(f"/api/videos/{video_id}", headers=other_headers).status_code == 404
    assert deleted_paths == []


def test_missing_session_cannot_receive_video(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")

    assert create_video(client, headers, 999).status_code == 404


@pytest.mark.parametrize(
    "storage_path",
    [
        "",
        "   ",
        "other/video.mp4",
        "videos/../video.mp4",
        "videos\\video.mp4",
        "videos/video.avi",
    ],
)
def test_video_rejects_invalid_storage_path(client_and_engine, storage_path: str) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)

    assert create_video(client, headers, session_id, storage_path).status_code == 422


def test_duplicate_storage_paths_are_allowed_without_a_schema_constraint(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)

    assert create_video(client, headers, session_id).status_code == 201
    assert create_video(client, headers, session_id).status_code == 201
    assert len(client.get(f"/api/sessions/{session_id}/videos", headers=headers).json()) == 2


def test_session_can_have_at_most_five_videos(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    session_id = create_session(client, headers)

    for index in range(5):
        response = create_video(
            client,
            headers,
            session_id,
            f"videos/user-1/session-{session_id}/video-{index}.mp4",
        )
        assert response.status_code == 201

    sixth_video = create_video(
        client,
        headers,
        session_id,
        f"videos/user-1/session-{session_id}/video-5.mp4",
    )

    assert sixth_video.status_code == 409
    assert sixth_video.json()["detail"] == "A session can have at most 5 videos"


def test_each_session_has_an_independent_five_video_limit(client_and_engine) -> None:
    client, _ = client_and_engine
    headers = signup_and_headers(client, "user@example.com", "climber01")
    first_session_id = create_session(client, headers)
    second_session_id = create_session(client, headers)

    for index in range(5):
        assert create_video(
            client,
            headers,
            first_session_id,
            f"videos/user-1/session-{first_session_id}/video-{index}.mp4",
        ).status_code == 201

    assert create_video(
        client,
        headers,
        second_session_id,
        f"videos/user-1/session-{second_session_id}/video-0.mp4",
    ).status_code == 201
