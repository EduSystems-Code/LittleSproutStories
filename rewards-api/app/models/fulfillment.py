from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.time_utils import utcnow


class Fulfillment(Base):
    """A mailing address (and, for apparel, a size/variant) submitted
    after a paid Order -- covers both the reward box and any Shop item.
    Only what's needed to address a package -- no child PII beyond a
    first name, which is optional and only used to personalize the
    reward box's certificate (meaningless for Shop items, left blank)."""

    __tablename__ = "fulfillments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))

    recipient_name: Mapped[str] = mapped_column(String(120))
    child_first_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Free-text size/color selection for apparel (e.g. "Youth Medium").
    # Null for products with no variant (the reward box, the bottle, the cap).
    variant: Mapped[str | None] = mapped_column(String(80), nullable=True)
    address_line1: Mapped[str] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="US")

    # Printify's order id, once a made-to-order Shop product has been
    # pushed to production (app/services/printify.py). Null for the
    # hand-kitted reward box and for any Printify-fulfilled order that
    # fell back to manual handling because Printify was unreachable.
    printify_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Set once services/retention.py has deleted the address fields below
    # this point -- the row itself is kept (for count/audit purposes) but
    # scrubbed of anything a name/address could be reconstructed from.
    scrubbed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
