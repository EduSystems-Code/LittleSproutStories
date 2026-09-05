"""Thin wrapper around Stripe Checkout. Every call here checks for a
configured API key at the point of use and raises a clear, specific error
rather than letting the app fail to start (see config.py's own docstring
for why) -- this whole feature is expected to be dark until the user has
a real Stripe payments account connected.

A completed Checkout payment replaces the old Stripe Identity step
entirely: the FTC lists "check a form of payment, such as a credit card"
as its own approved method of verifiable parental consent under COPPA,
so a real $10 charge does double duty -- proof of payment AND proof of
consent -- for a fraction of Identity's ~$1-1.50/check cost, and with a
much stronger anti-abuse property (a bot can't supply a real card that
clears)."""
import stripe
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.order import Order
from app.products import get_product


class StripeNotConfigured(RuntimeError):
    """Raised at the point a Stripe call is actually attempted, not at
    import/startup time -- lets the rest of the app (health check, the
    admin dashboard for already-submitted requests) work before Stripe
    is wired up."""


class UnknownProduct(ValueError):
    """A product_id that isn't in app.products.PRODUCTS -- a bad request,
    not a server error."""


def _client() -> None:
    settings = get_settings()
    if not settings.stripe_api_key:
        raise StripeNotConfigured(
            "STRIPE_API_KEY is not set. Selling anything requires a real "
            "Stripe payments account and API key in .env."
        )
    stripe.api_key = settings.stripe_api_key


def create_checkout_session(db: Session, product_id: str = "reward_box") -> tuple[Order, str]:
    """Returns (the DB record, Stripe's hosted Checkout URL). The URL comes
    back on the create() response itself -- no need for a second Stripe API
    call to fetch it. The return page is the same rewards.html for every
    product -- it reads the order back via /checkout/status and asks for a
    shipping address once paid, regardless of what was bought."""
    product = get_product(product_id)
    if product is None:
        raise UnknownProduct(product_id)

    _client()
    settings = get_settings()
    record = Order(product_id=product_id, amount_cents=product["price_cents"])
    db.add(record)
    db.commit()
    db.refresh(record)

    # The reward box returns to rewards.html (its own copy/flow); every
    # Shop item returns to shop.html instead, so a t-shirt buyer doesn't
    # land on a page talking about finishing 14 books.
    return_page = settings.rewards_page_url if product_id == "reward_box" else settings.shop_page_url

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": product["price_cents"],
                "product_data": {
                    "name": product["name"],
                    "description": product["description"],
                },
            },
            "quantity": 1,
        }],
        success_url=f"{return_page}?token={record.token}",
        cancel_url=f"{return_page}?token={record.token}&cancelled=1",
        client_reference_id=record.token,
    )
    record.stripe_checkout_session_id = session.id
    db.commit()
    db.refresh(record)
    return record, session.url


def verify_webhook_signature(payload: bytes, sig_header: str) -> stripe.Event:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise StripeNotConfigured("STRIPE_WEBHOOK_SECRET is not set.")
    return stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)


def mark_paid_from_event(db: Session, event: stripe.Event) -> Order | None:
    """Handles checkout.session.completed. Returns the updated row, or None
    if the event doesn't match an order we created (should only happen for
    a stray/replayed webhook, not a normal flow). Also guards against a
    Checkout session that completed without actually collecting payment
    (e.g. a free/$0 line item) -- `payment_status` must be "paid"."""
    from app.time_utils import utcnow

    if event["type"] != "checkout.session.completed":
        return None
    session_obj = event["data"]["object"]
    if session_obj.get("payment_status") != "paid":
        return None
    stripe_checkout_session_id = session_obj["id"]
    record = (
        db.query(Order)
        .filter(Order.stripe_checkout_session_id == stripe_checkout_session_id)
        .one_or_none()
    )
    if record is None:
        return None
    record.paid = True
    record.paid_at = utcnow()
    db.commit()
    db.refresh(record)
    return record
