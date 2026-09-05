"""Scrubs mailing-address fields off any Fulfillment that was marked
sent more than settings.retention_days_after_sent ago. Run this on every
admin-dashboard login (cheap at this volume -- no need for a scheduled
job/cron on a free-tier host) rather than only on a timer, so retention
stays honest even if the app has been asleep (Render free tier spins
down on idle) for longer than the retention window itself.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.fulfillment import Fulfillment
from app.time_utils import utcnow


def scrub_expired(db: Session) -> int:
    settings = get_settings()
    cutoff = utcnow() - timedelta(days=settings.retention_days_after_sent)
    expired = (
        db.query(Fulfillment)
        .filter(Fulfillment.sent_at.isnot(None))
        .filter(Fulfillment.sent_at < cutoff)
        .filter(Fulfillment.scrubbed_at.is_(None))
        .all()
    )
    for row in expired:
        row.recipient_name = "[scrubbed]"
        row.child_first_name = None
        row.address_line1 = "[scrubbed]"
        row.address_line2 = None
        row.city = "[scrubbed]"
        row.state = "[scrubbed]"
        row.postal_code = "[scrubbed]"
        row.scrubbed_at = utcnow()
    if expired:
        db.commit()
    return len(expired)
