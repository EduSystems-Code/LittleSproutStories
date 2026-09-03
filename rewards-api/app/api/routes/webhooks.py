import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.stripe_checkout import (
    StripeNotConfigured,
    mark_paid_from_event,
    verify_webhook_signature,
)

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = verify_webhook_signature(payload, sig_header)
    except StripeNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except (stripe.error.SignatureVerificationError, ValueError) as e:
        # A bad/forged signature is a real security-relevant rejection --
        # 400, not a silent 200 that would let a spoofed event through.
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from e

    mark_paid_from_event(db, event)
    return {"status": "ok"}
