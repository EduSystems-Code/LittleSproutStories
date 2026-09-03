"""datetime.utcnow() is deprecated (and scheduled for removal) in favor of
timezone-aware datetimes -- but SQLite has no native timezone type, and
mixing naive (existing/stored) and aware datetimes raises a TypeError on
comparison. This returns a naive datetime that's still correctly UTC,
so every model/service in this app gets the fix without a bigger
timezone-aware storage migration."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
