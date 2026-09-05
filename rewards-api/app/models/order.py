import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.time_utils import utcnow


def _new_token() -> str:
    # Opaque, unguessable token the frontend holds between "paid via Stripe
    # Checkout" and "submitted the address form" -- never the raw Stripe
    # session ID (that's an implementation detail the client doesn't need).
    return secrets.token_urlsafe(32)


class Order(Base):
    """One row per checkout -- the reward box or any Shop item
    (app/products.py). `paid` is only ever set true by the webhook
    handler (services/stripe_checkout.py) reacting to Stripe's own signed
    `checkout.session.completed` event -- never trusted from the client.
    For the reward box specifically, a completed card charge is itself an
    FTC-approved COPPA "verifiable parental consent" method (payment), so
    that row does double duty: proof of payment AND proof of consent --
    no separate Stripe Identity step needed. Shop items are ordinary
    merchandise purchases with no consent implication."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=_new_token)
    # Key into app.products.PRODUCTS -- which catalog item this order is
    # for. Defaults to the original reward box for backward compatibility.
    product_id: Mapped[str] = mapped_column(String(40), default="reward_box")
    # Nullable: our own token is generated (and needed, for Stripe's
    # success_url) before Stripe hands back a session id -- two-step
    # insert-then-update, same shape as the old Identity flow.
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # A paid order is consumed by exactly one Fulfillment -- set once
    # /requests accepts it, so the same token can't be replayed.
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
