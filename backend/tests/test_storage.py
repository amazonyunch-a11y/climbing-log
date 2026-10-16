import httpx
import pytest

from app.core.config import get_settings
from app.services.storage import StorageConfigurationError, delete_storage_object


def test_delete_storage_object_treats_missing_file_as_already_deleted(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    get_settings.cache_clear()
    calls: list[dict[str, object]] = []

    def fake_delete(url: str, **kwargs: object) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        return httpx.Response(404, json={"code": "NoSuchKey"})

    monkeypatch.setattr("app.services.storage.httpx.delete", fake_delete)

    delete_storage_object("videos/user-1/session-10/missing.mp4")

    assert calls[0]["url"] == (
        "https://test-project.supabase.co/storage/v1/object/"
        "climbing-videos/videos/user-1/session-10/missing.mp4"
    )
    headers = calls[0]["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer service-role-test-key"
    get_settings.cache_clear()


def test_delete_storage_object_requires_server_only_service_role_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(StorageConfigurationError):
        delete_storage_object("videos/user-1/session-10/video.mp4")

    get_settings.cache_clear()
