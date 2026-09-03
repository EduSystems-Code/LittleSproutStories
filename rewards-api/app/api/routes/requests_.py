"""Named requests_.py (not requests.py) to avoid shadowing the `requests`
package if it's ever imported anywhere in this app -- a real footgun in a
FastAPI project this size."""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.fulfillment import Fulfillment
from app.models.order import Order
from app.products import get_product, known_variants
from app.schemas.requests import FulfillmentIn, FulfillmentOut
from app.services.printify import PrintifyNotConfigured, create_and_produce_order

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/requests", response_model=FulfillmentOut, status_code=201)
def submit_request(payload: FulfillmentIn, db: Session = Depends(get_db)) -> Fulfillment:
    order = db.query(Order).filter(Order.token == payload.token).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Unknown or expired checkout token")
    if not order.paid:
        # Never trust a client-reported "I paid" -- only the webhook
        # (services/stripe_checkout.py, reacting to Stripe's own signed
        # event) is allowed to flip this.
        raise HTTPException(status_code=403, detail="Payment not yet complete")
    if order.consumed:
        raise HTTPException(status_code=409, detail="This order has already been used for a request")

    # Validate the size/variant against the catalog rather than storing
    # whatever free text arrived -- a wrong value here becomes a misprint.
    allowed = known_variants(order.product_id)
    if allowed:
        if not payload.variant:
            raise HTTPException(status_code=422, detail="This product needs a size selection")
        if payload.variant not in allowed:
            raise HTTPException(status_code=422, detail=f"Unknown size: {payload.variant}")
    elif payload.variant:
        raise HTTPException(status_code=422, detail="This product has no size selection")

    record = Fulfillment(
        order_id=order.id,
        recipient_name=payload.recipient_name,
        child_first_name=payload.child_first_name,
        variant=payload.variant,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
    )
    order.consumed = True
    db.add(record)
    db.commit()
    db.refresh(record)

    # Made-to-order Shop products go straight to Printify. A failure here
    # (unconfigured, or Printify unreachable) must NOT fail the buyer's
    # request -- they've paid and the address is saved; the row just shows
    # up unsent in the admin dashboard for manual handling.
    product = get_product(order.product_id) or {}
    if product.get("fulfillment") == "printify":
        try:
            record.printify_order_id = create_and_produce_order(record, order)
            db.commit()
            db.refresh(record)
        except (PrintifyNotConfigured, httpx.HTTPError) as e:
            logger.warning("Printify order not placed for order %s (%s): %s", order.id, order.product_id, e)

    return record
