from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def utc_now() -> datetime:
    """Return a timezone-naive datetime whose value is UTC for current DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def kst_input_to_utc(value: datetime) -> datetime:
    """Interpret offset-free input as KST, then return a UTC-naive DB value."""
    kst_value = value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)
    return kst_value.astimezone(timezone.utc).replace(tzinfo=None)


def utc_to_iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def utc_to_kst_date(value: datetime) -> date:
    return value.replace(tzinfo=timezone.utc).astimezone(KST).date()


def kst_date_to_utc_range(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min, tzinfo=KST)
    end = datetime.combine(value.fromordinal(value.toordinal() + 1), time.min, tzinfo=KST)
    return (
        start.astimezone(timezone.utc).replace(tzinfo=None),
        end.astimezone(timezone.utc).replace(tzinfo=None),
    )
