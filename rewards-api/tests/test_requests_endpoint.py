"""POST /api/requests -- the endpoint that actually stores a mailing
address. Every acceptance/rejection path gets its own test since this is
the one place a real address gets written."""
from tests.conftest import make_paid_order

VALID_PAYLOAD = {
    "token": "placeholder",
    "recipient_name": "Jane Parent",
    "child_first_name": "Sam",
    "address_line1": "123 Main St",
    "city": "Baltimore",
    "state": "MD",
    "postal_code": "21201",
}


def test_rejects_unknown_token(client):
    r = client.post("/api/requests", json={**VALID_PAYLOAD, "token": "not-a-real-token"})
    assert r.status_code == 404


def test_rejects_unpaid_order(client, db_session):
    from app.models.order import Order

    order = Order(stripe_checkout_session_id="cs_unpaid", amount_cents=1000, paid=False)
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    r = client.post("/api/requests", json={**VALID_PAYLOAD, "token": order.token})
    assert r.status_code == 403


def test_accepts_paid_order(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_ok")
    r = client.post("/api/requests", json={**VALID_PAYLOAD, "token": order.token})
    assert r.status_code == 201
    body = r.json()
    assert body["recipient_name"] == "Jane Parent"
    assert body["sent_at"] is None


def test_rejects_replayed_token(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_replay")
    r1 = client.post("/api/requests", json={**VALID_PAYLOAD, "token": order.token})
    assert r1.status_code == 201

    r2 = client.post("/api/requests", json={**VALID_PAYLOAD, "token": order.token})
    assert r2.status_code == 409
