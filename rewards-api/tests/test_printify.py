"""Printify made-to-order fulfillment: the payload builder is a pure
function, and POST /api/requests wires it in so that a Printify failure
never costs the buyer their (already paid) order."""
import httpx
import pytest

from app.models.fulfillment import Fulfillment
from app.models.order import Order
from app.products import PRODUCTS
from app.services import printify as printify_service
from app.services.printify import PrintifyNotConfigured, build_order_payload
from tests.conftest import TEST_ADMIN_PASSWORD, make_paid_order

ADDR = {
    "recipient_name": "Jane Parent",
    "address_line1": "123 Main St",
    "city": "Baltimore",
    "state": "MD",
    "postal_code": "21201",
}


CONTACT = {"contact_email": "orders@example.test", "contact_phone": "555-0100"}


def test_build_order_payload_sized_product():
    order = Order(id=7, token="tok_abc", product_id="tshirt", amount_cents=2000)
    fulfillment = Fulfillment(
        recipient_name="Jane Q Parent", variant="YM",
        address_line1="123 Main St", address_line2="Apt 4",
        city="Baltimore", state="MD", postal_code="21201", country="US",
    )
    product = {
        "name": "Little Sprout T-Shirt",
        "variants": ["YS", "YM", "YL"],
        "printify": {
            "blueprint_id": 5, "print_provider_id": 9,
            "image_url": "https://img.example/tee.png",
            "variant_id": None,
            "variants": {"YS": 100, "YM": 101, "YL": 102},
        },
    }

    payload = build_order_payload(fulfillment, order, product, **CONTACT)

    li = payload["line_items"][0]
    assert payload["external_id"] == "tok_abc"
    assert li["variant_id"] == 101
    assert li["blueprint_id"] == 5
    assert li["print_provider_id"] == 9
    assert li["print_areas"] == {"front": "https://img.example/tee.png"}
    assert payload["address_to"]["first_name"] == "Jane Q"
    assert payload["address_to"]["last_name"] == "Parent"
    assert payload["address_to"]["address2"] == "Apt 4"
    assert payload["address_to"]["zip"] == "21201"
    assert payload["address_to"]["email"] == "orders@example.test"
    assert payload["address_to"]["phone"] == "555-0100"


def test_build_order_payload_unsized_product_uses_single_variant_id():
    order = Order(id=8, token="tok_tote", product_id="tote", amount_cents=1500)
    fulfillment = Fulfillment(
        recipient_name="Sam", variant=None,
        address_line1="1 A St", city="Baltimore", state="MD",
        postal_code="21201", country="US",
    )
    product = {
        "name": "Little Sprout Library Bag",
        "variants": None,
        "printify": {
            "blueprint_id": 42, "print_provider_id": 7,
            "image_url": "https://img.example/tote.png",
            "variant_id": 999, "variants": {},
        },
    }

    payload = build_order_payload(fulfillment, order, product, **CONTACT)

    assert payload["line_items"][0]["variant_id"] == 999
    # single-word name repeated so neither Printify name field is blank
    assert payload["address_to"]["first_name"] == "Sam"
    assert payload["address_to"]["last_name"] == "Sam"


def test_create_and_produce_order_unconfigured_raises():
    # No PRINTIFY_* env in the test environment.
    order = Order(id=1, token="t", product_id="tshirt", amount_cents=2000)
    with pytest.raises(PrintifyNotConfigured):
        printify_service.create_and_produce_order(Fulfillment(**ADDR), order)


def test_reward_box_never_calls_printify(client, db_session, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("Printify must not be called for the reward box")

    monkeypatch.setattr("app.api.routes.requests_.create_and_produce_order", boom)
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_rb", product_id="reward_box")
    r = client.post("/api/requests", json={"token": order.token, **ADDR})
    assert r.status_code == 201
    assert r.json().get("printify_order_id") in (None, "")


def test_printify_success_persists_order_id(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.requests_.create_and_produce_order",
        lambda fulfillment, order: "pfy_12345",
    )
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_ok", amount_cents=1500, product_id="tote")
    r = client.post("/api/requests", json={"token": order.token, **ADDR})
    assert r.status_code == 201

    row = db_session.query(Fulfillment).filter(Fulfillment.order_id == order.id).one()
    assert row.printify_order_id == "pfy_12345"


def test_printify_failure_still_returns_201(client, db_session, monkeypatch):
    def fail(fulfillment, order):
        raise httpx.HTTPError("Printify 500")

    monkeypatch.setattr("app.api.routes.requests_.create_and_produce_order", fail)
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_fail", amount_cents=1500, product_id="tote")
    r = client.post("/api/requests", json={"token": order.token, **ADDR})
    assert r.status_code == 201

    db_session.expire_all()
    row = db_session.query(Fulfillment).filter(Fulfillment.order_id == order.id).one()
    assert row.printify_order_id is None
    # the order is still consumed -- a downstream vendor failure doesn't
    # roll back the address we already stored
    assert db_session.get(Order, order.id).consumed is True


def test_unknown_variant_rejected(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_bad_var", amount_cents=2000, product_id="tshirt")
    r = client.post("/api/requests", json={"token": order.token, "variant": "XXL", **ADDR})
    assert r.status_code == 422


def test_missing_required_variant_rejected(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_no_var", amount_cents=2000, product_id="tshirt")
    r = client.post("/api/requests", json={"token": order.token, **ADDR})
    assert r.status_code == 422


def test_variant_on_non_variant_product_rejected(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_extra_var", amount_cents=1500, product_id="tote")
    r = client.post("/api/requests", json={"token": order.token, "variant": "YM", **ADDR})
    assert r.status_code == 422


def test_catalog_shop_products_all_have_printify_mapping():
    expected = {"blueprint_id", "print_provider_id", "image_url", "variant_id", "variants"}
    for pid, product in PRODUCTS.items():
        if product.get("fulfillment") == "printify":
            assert "printify" in product, pid
            assert set(product["printify"]) == expected, pid
