import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


logger = logging.getLogger(__name__)
DEFAULT_EXPORT_TIMEZONE = "America/Phoenix"


def get_export_now() -> datetime:
    tz_name = os.getenv("EXPORT_TIMEZONE", DEFAULT_EXPORT_TIMEZONE)
    try:
        export_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning("Invalid EXPORT_TIMEZONE=%r; falling back to UTC", tz_name)
        export_tz = timezone.utc
    return datetime.now(timezone.utc).astimezone(export_tz)
