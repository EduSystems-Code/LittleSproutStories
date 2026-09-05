from datetime import timedelta

from app.models.fulfillment import Fulfillment
from app.services.retention import scrub_expired
from app.time_utils import utcnow
from tests.conftest import make_paid_order


def test_scrubs_only_old_sent_requests(db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_retention")

    old_sent = Fulfillment(
        order_id=order.id, recipient_name="Old Parent",
        address_line1="1 Old St", city="X", state="Y", postal_code="11111",
        sent_at=utcnow() - timedelta(days=100),
    )
    recent_sent = Fulfillment(
        order_id=order.id, recipient_name="Recent Parent",
        address_line1="2 New St", city="X", state="Y", postal_code="22222",
        sent_at=utcnow() - timedelta(days=10),
    )
    never_sent = Fulfillment(
        order_id=order.id, recipient_name="Pending Parent",
        address_line1="3 Pending Ave", city="X", state="Y", postal_code="33333",
        sent_at=None,
    )
    db_session.add_all([old_sent, recent_sent, never_sent])
    db_session.commit()

    scrubbed_count = scrub_expired(db_session)
    assert scrubbed_count == 1

    db_session.refresh(old_sent)
    db_session.refresh(recent_sent)
    db_session.refresh(never_sent)

    assert old_sent.scrubbed_at is not None
    assert old_sent.recipient_name == "[scrubbed]"
    assert old_sent.address_line1 == "[scrubbed]"

    assert recent_sent.scrubbed_at is None
    assert recent_sent.recipient_name == "Recent Parent"

    assert never_sent.scrubbed_at is None
    assert never_sent.recipient_name == "Pending Parent"


def test_scrubbed_requests_disappear_from_admin_list(client, db_session):
    from tests.conftest import TEST_ADMIN_PASSWORD

    order = make_paid_order(db_session, stripe_checkout_session_id="cs_retention_admin")
    old_sent = Fulfillment(
        order_id=order.id, recipient_name="Old Parent",
        address_line1="1 Old St", city="X", state="Y", postal_code="11111",
        sent_at=utcnow() - timedelta(days=100),
    )
    db_session.add(old_sent)
    db_session.commit()

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    # the admin list endpoint sweeps expired requests on every load
    listing = client.get("/api/admin/requests")
    assert listing.status_code == 200
    assert listing.json() == []
