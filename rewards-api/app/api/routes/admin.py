from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.models.board_post import BoardPost
from app.models.fulfillment import Fulfillment
from app.models.order import Order
from app.products import get_product
from app.schemas.board import BoardPostAdminOut
from app.schemas.requests import FulfillmentOut
from app.services.admin_auth import (
    COOKIE_NAME,
    check_password,
    is_valid_session_cookie,
    make_session_cookie,
)
from app.services.retention import scrub_expired
from app.time_utils import utcnow

router = APIRouter()


class AdminLoginIn(BaseModel):
    password: str


def require_admin(rewards_admin: str | None = Cookie(default=None)) -> None:
    if not is_valid_session_cookie(rewards_admin):
        raise HTTPException(status_code=401, detail="Not logged in")


@router.post("/admin/login")
def admin_login(payload: AdminLoginIn, response: Response) -> dict[str, str]:
    if not check_password(payload.password):
        raise HTTPException(status_code=401, detail="Wrong password")
    response.set_cookie(
        COOKIE_NAME,
        make_session_cookie(),
        httponly=True,
        secure=get_settings().admin_cookie_secure,
        # "none", not "strict": the admin dashboard is a static page on
        # GitHub Pages calling this API on Render -- a different origin,
        # so this is inherently a cross-site request. A SameSite=Strict
        # (or even Lax) cookie is never sent cross-site at all, credentials
        # or not, which would silently break every admin request after
        # login. SameSite=None requires Secure=True, which is already the
        # default here (admin_cookie_secure); only local dev over plain
        # http needs to turn Secure off, at which point SameSite=None
        # cookies are refused anyway -- see conftest.py's test override.
        samesite="none" if get_settings().admin_cookie_secure else "lax",
        max_age=60 * 60 * 12,
    )
    return {"status": "ok"}


@router.get("/admin/requests", response_model=list[FulfillmentOut], dependencies=[Depends(require_admin)])
def list_requests(db: Session = Depends(get_db)) -> list[FulfillmentOut]:
    scrub_expired(db)  # sweep on every dashboard load -- see services/retention.py
    rows = (
        db.query(Fulfillment, Order)
        .join(Order, Fulfillment.order_id == Order.id)
        .filter(Fulfillment.scrubbed_at.is_(None))
        .order_by(Fulfillment.sent_at.is_(None).desc(), Fulfillment.created_at.asc())
        .all()
    )
    out = []
    for fulfillment, order in rows:
        product = get_product(order.product_id) or {}
        item = FulfillmentOut.model_validate(fulfillment)
        item.product_id = order.product_id
        item.product_name = product.get("name")
        out.append(item)
    return out


@router.post("/admin/requests/{request_id}/mark-sent", dependencies=[Depends(require_admin)])
def mark_sent(request_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    record = db.get(Fulfillment, request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    record.sent_at = utcnow()
    db.commit()
    return {"status": "ok"}


@router.get("/admin/board/posts", response_model=list[BoardPostAdminOut], dependencies=[Depends(require_admin)])
def list_board_posts(db: Session = Depends(get_db)) -> list[BoardPost]:
    """Pending first (the actual moderation queue), then everything
    already decided, most recent submission first within each group."""
    return (
        db.query(BoardPost)
        .order_by(BoardPost.approved.asc(), BoardPost.created_at.desc())
        .all()
    )


@router.post("/admin/board/posts/{post_id}/approve", dependencies=[Depends(require_admin)])
def approve_board_post(post_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    record = db.get(BoardPost, post_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    record.approved = True
    record.approved_at = utcnow()
    db.commit()
    return {"status": "ok"}


@router.post("/admin/board/posts/{post_id}/reject", dependencies=[Depends(require_admin)])
def reject_board_post(post_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Rejecting deletes the row outright -- there's no public-facing
    "rejected" state to preserve, and an unapproved submission carries an
    email address that shouldn't linger once a human has decided no."""
    record = db.get(BoardPost, post_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(record)
    db.commit()
    return {"status": "ok"}
