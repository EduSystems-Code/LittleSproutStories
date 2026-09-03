"""The product catalog and checkout-start's product handling -- the Shop
adds multiple purchasable products sharing one Checkout/fulfillment
pipeline, so this covers the parts specific to that generalization."""
from app.products import PRODUCTS


def test_products_endpoint_lists_shop_items_only(client):
    r = client.get("/api/products")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    # the reward box is reached only via the badge-shelf CTA, not the
    # general Shop -- it must never show up here
    assert "reward_box" not in ids
    assert {"tshirt", "hat", "water_bottle"} <= ids


def test_products_endpoint_prices_match_catalog(client):
    r = client.get("/api/products")
    by_id = {p["id"]: p for p in r.json()}
    assert by_id["tshirt"]["price_cents"] == PRODUCTS["tshirt"]["price_cents"]
    assert by_id["tshirt"]["variants"] == PRODUCTS["tshirt"]["variants"]


def test_checkout_start_rejects_unknown_product(client):
    r = client.post("/api/checkout/start", json={"product_id": "not-a-real-product"})
    assert r.status_code == 404


def test_checkout_start_without_stripe_configured_returns_503(client):
    # STRIPE_API_KEY is unset in the test env (see conftest.py) -- both the
    # reward box and a Shop item should fail the same clear, expected way.
    r = client.post("/api/checkout/start", json={"product_id": "reward_box"})
    assert r.status_code == 503

    r2 = client.post("/api/checkout/start", json={"product_id": "tshirt"})
    assert r2.status_code == 503


def test_requests_endpoint_stores_variant_for_apparel(client, db_session):
    from tests.conftest import make_paid_order

    order = make_paid_order(db_session, stripe_checkout_session_id="cs_tshirt", amount_cents=2000, product_id="tshirt")
    r = client.post("/api/requests", json={
        "token": order.token,
        "recipient_name": "Jane Parent",
        "variant": "YM",
        "address_line1": "123 Main St",
        "city": "Baltimore",
        "state": "MD",
        "postal_code": "21201",
    })
    assert r.status_code == 201
    assert r.json()["variant"] == "YM"


def test_admin_list_shows_product_for_each_request(client, db_session):
    from tests.conftest import TEST_ADMIN_PASSWORD, make_paid_order

    order = make_paid_order(db_session, stripe_checkout_session_id="cs_hat", amount_cents=1800, product_id="hat")
    client.post("/api/requests", json={
        "token": order.token,
        "recipient_name": "Jane Parent",
        "address_line1": "123 Main St",
        "city": "Baltimore",
        "state": "MD",
        "postal_code": "21201",
    })

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    listing = client.get("/api/admin/requests")
    assert listing.status_code == 200
    row = listing.json()[0]
    assert row["product_id"] == "hat"
    assert row["product_name"] == "Little Sprout Cap"
