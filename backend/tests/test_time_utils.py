import os
import pytest
from datetime import timezone

from backend.time_utils import get_export_now


def test_returns_datetime_with_tzinfo():
    result = get_export_now()
    assert result.tzinfo is not None


def test_default_timezone_is_phoenix(monkeypatch):
    monkeypatch.delenv("EXPORT_TIMEZONE", raising=False)
    result = get_export_now()
    tz_name = result.tzname()
    assert tz_name in ("MST", "MDT"), f"Expected MST or MDT, got {tz_name!r}"


def test_custom_valid_timezone(monkeypatch):
    monkeypatch.setenv("EXPORT_TIMEZONE", "America/New_York")
    result = get_export_now()
    tz_name = result.tzname()
    assert tz_name in ("EST", "EDT"), f"Expected EST or EDT, got {tz_name!r}"


def test_invalid_timezone_falls_back_to_utc(monkeypatch):
    monkeypatch.setenv("EXPORT_TIMEZONE", "Bad/Zone")
    result = get_export_now()
    assert result.tzinfo == timezone.utc
