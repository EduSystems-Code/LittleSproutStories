from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.order import Order
from app.products import get_product, shop_products
from app.schemas.requests import CheckoutStartIn, CheckoutStartResponse, ProductOut
from app.services.stripe_checkout import StripeNotConfigured, UnknownProduct, create_checkout_session

router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
def list_products() -> list[dict]:
    """Everything the Shop page should show -- a single source of truth so
    the frontend never hardcodes a price that could drift from what
    Checkout actually charges."""
    return [{"id": k, **v} for k, v in shop_products().items()]


@router.post("/checkout/start", response_model=CheckoutStartResponse)
def start_checkout(payload: CheckoutStartIn, db: Session = Depends(get_db)) -> CheckoutStartResponse:
    if get_product(payload.product_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown product: {payload.product_id}")
    try:
        record, checkout_url = create_checkout_session(db, product_id=payload.product_id)
    except StripeNotConfigured as e:
        # 503, not 500: this is an expected, temporary "not wired up yet"
        # state (pending a real Stripe payments account), not a real bug.
        raise HTTPException(status_code=503, detail=str(e)) from e
    except UnknownProduct as e:
        raise HTTPException(status_code=404, detail=f"Unknown product: {e}") from e
    return CheckoutStartResponse(checkout_url=checkout_url, token=record.token)


@router.get("/checkout/status")
def checkout_status(token: str, db: Session = Depends(get_db)) -> dict:
    """Stripe's webhook (POST /webhooks/stripe) is the only thing that ever
    sets `paid`, and it's async -- a buyer can land back on the return page
    (Stripe's own success_url) before that webhook has actually arrived and
    been processed. The frontend polls this instead of assuming payment is
    done the instant the user is redirected back."""
    order = db.query(Order).filter(Order.token == token).one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Unknown token")
    product = get_product(order.product_id) or {}
    return {
        "paid": order.paid,
        "consumed": order.consumed,
        "product_id": order.product_id,
        "product_name": product.get("name"),
        "variants": product.get("variants"),
    }
