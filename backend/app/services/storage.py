from urllib.parse import quote

import httpx

from app.core.config import get_settings


class StorageDeletionError(RuntimeError):
    """Raised when Supabase Storage cannot delete an object safely."""


class StorageConfigurationError(StorageDeletionError):
    """Raised when server-only Supabase Storage settings are unavailable."""


def delete_storage_object(storage_path: str) -> None:
    """Delete one Storage object with the server-only service role key.

    A missing object is treated as already deleted so its stale metadata can be
    removed. Other Storage errors leave metadata untouched for a later retry.
    """
    settings = get_settings()
    if (
        not settings.supabase_url
        or not settings.supabase_storage_bucket
        or not settings.supabase_service_role_key
    ):
        raise StorageConfigurationError("Supabase Storage delete settings are required")

    try:
        response = httpx.delete(
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{quote(settings.supabase_storage_bucket, safe='')}/"
            f"{quote(storage_path, safe='/')}",
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
            },
            timeout=10.0,
        )
    except httpx.HTTPError as error:
        raise StorageDeletionError("Supabase Storage request failed") from error

    if response.is_success:
        return

    try:
        error_code = response.json().get("code")
    except (ValueError, AttributeError):
        error_code = None
    if response.status_code == 404 and error_code == "NoSuchKey":
        return

    raise StorageDeletionError(
        f"Supabase Storage delete failed with status {response.status_code}"
    )


def build_public_file_url(storage_path: str) -> str:
    """Build a Supabase Storage public-object URL without requiring a service key."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_storage_bucket:
        raise RuntimeError("Supabase Storage public URL settings are required")

    return (
        f"{settings.supabase_url.rstrip('/')}"
        f"/storage/v1/object/public/{settings.supabase_storage_bucket}"
        f"/{quote(storage_path, safe='/')}"
    )
