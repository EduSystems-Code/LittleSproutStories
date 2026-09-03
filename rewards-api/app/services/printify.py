"""Thin wrapper around the Printify orders API -- the same shape as
services/stripe_checkout.py: every call checks for configuration at the
point of use and raises a clear, specific error rather than failing at
import/startup, because this feature is dark until the user has a real
Printify account connected.

The one caller is POST /api/requests (api/routes/requests_.py): once a
paid order's shipping address is stored, a made-to-order Shop product
(app/products.py -> "fulfillment": "printify") gets a Printify order
created and pushed straight to production. The reward box never comes
here -- it's hand-kitted and shipped from a 3PL.

Failure here is never allowed to fail the buyer's request: the caller
catches PrintifyNotConfigured and httpx errors, keeps the 201, and the
row shows up unsent in the admin dashboard for manual handling.
"""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.models.fulfillment import Fulfillment
from app.models.order import Order
from app.products import get_product, printify_mapping_ready

API_ROOT = "https://api.printify.com/v1"
_TIMEOUT = 20.0


class PrintifyNotConfigured(RuntimeError):
    """Raised at the point a Printify call is attempted -- no API token,
    no shop id, or the product's catalog mapping still has placeholder
    ids. Treated by the caller as 'not wired up yet', identical to the
    Stripe-unconfigured path, not a bug."""


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # Printify asks integrations to send a UA identifying the app.
        "User-Agent": "LittleSprout-Rewards",
    }


def build_order_payload(fulfillment: Fulfillment, order: Order, product: dict) -> dict:
    """Pure function -- turns a stored Fulfillment + its Order + the
    catalog entry into the JSON body Printify's create-order endpoint
    expects. Kept separate from the HTTP call so it can be asserted on
    directly in tests."""
    mapping = product["printify"]

    line_item: dict = {
        "print_provider_id": mapping["print_provider_id"],
        "blueprint_id": mapping["blueprint_id"],
        "quantity": 1,
        "print_areas": {"front": mapping["image_id"]},
    }
    size = fulfillment.variant
    if size:
        # validated upstream (requests_.py) against known_variants()
        line_item["variant_id"] = mapping["variants"][size]

    # Printify wants first/last split; our form collects a single
    # recipient name. Split on the last space, fall back to a repeat so
    # neither field is empty (Printify rejects blank names).
    name = (fulfillment.recipient_name or "").strip()
    if " " in name:
        first_name, last_name = name.rsplit(" ", 1)
    else:
        first_name = last_name = name or "Reader"

    return {
        "external_id": order.token,
        "label": f"{product['name']} (order {order.id})",
        "line_items": [line_item],
        "shipping_method": 1,  # standard
        "send_shipping_notification": False,
        "address_to": {
            "first_name": first_name,
            "last_name": last_name,
            "email": "",
            "phone": "",
            "country": fulfillment.country or "US",
            "region": fulfillment.state,
            "address1": fulfillment.address_line1,
            "address2": fulfillment.address_line2 or "",
            "city": fulfillment.city,
            "zip": fulfillment.postal_code,
        },
    }


def _post(path: str, token: str, json: dict | None = None) -> httpx.Response:
    """Single seam for the network call -- tests monkeypatch this."""
    resp = httpx.post(f"{API_ROOT}{path}", headers=_auth_headers(token), json=json, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp


def create_and_produce_order(fulfillment: Fulfillment, order: Order) -> str:
    """Create a Printify order for a made-to-order Shop product and send
    it to production. Returns the Printify order id.

    Raises PrintifyNotConfigured if the token/shop id are unset or the
    product's mapping is still a placeholder. Lets httpx.HTTPError
    propagate -- the caller handles both by falling back to manual
    fulfillment."""
    settings = get_settings()
    token = settings.printify_api_token
    shop_id = settings.printify_shop_id
    if not token or not shop_id:
        raise PrintifyNotConfigured(
            "PRINTIFY_API_TOKEN / PRINTIFY_SHOP_ID are not set. Made-to-order "
            "fulfillment requires a real Printify account."
        )

    product = get_product(order.product_id)
    if product is None or product.get("fulfillment") != "printify":
        raise PrintifyNotConfigured(f"{order.product_id} is not a Printify-fulfilled product")
    if not printify_mapping_ready(product):
        raise PrintifyNotConfigured(
            f"{order.product_id} has no complete Printify catalog mapping yet"
        )

    payload = build_order_payload(fulfillment, order, product)
    created = _post(f"/shops/{shop_id}/orders.json", token, json=payload)
    printify_order_id = str(created.json()["id"])
    _post(f"/shops/{shop_id}/orders/{printify_order_id}/send_to_production.json", token)
    return printify_order_id
