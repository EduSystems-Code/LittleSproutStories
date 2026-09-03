from tests.conftest import make_paid_order


def test_status_rejects_unknown_token(client):
    r = client.get("/api/checkout/status", params={"token": "not-real"})
    assert r.status_code == 404


def test_status_reports_unpaid_order(client, db_session):
    from app.models.order import Order

    order = Order(stripe_checkout_session_id="cs_pending", amount_cents=1000, paid=False)
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    r = client.get("/api/checkout/status", params={"token": order.token})
    assert r.status_code == 200
    body = r.json()
    assert body["paid"] is False
    assert body["consumed"] is False
    assert body["product_id"] == "reward_box"


def test_status_reports_paid_order(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_done")
    r = client.get("/api/checkout/status", params={"token": order.token})
    assert r.status_code == 200
    body = r.json()
    assert body["paid"] is True
    assert body["consumed"] is False


def test_status_reports_product_and_variants_for_shop_item(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_shirt", amount_cents=2000, product_id="tshirt")
    r = client.get("/api/checkout/status", params={"token": order.token})
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == "tshirt"
    assert body["product_name"] == "Little Sprout T-Shirt"
    assert "YM" in body["variants"]
