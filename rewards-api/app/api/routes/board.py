from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.board_post import BoardPost
from app.schemas.board import BOARD_CATEGORIES, BoardPostIn, BoardPostOut
from app.services.board_moderation import enforce_rate_limit, screen_post

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    # Render (and most PaaS hosts) sit behind a proxy, so request.client.host
    # is the proxy's own address -- the real submitter is the first hop in
    # X-Forwarded-For when it's present.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/board/posts", response_model=BoardPostOut, status_code=201)
def submit_post(payload: BoardPostIn, request: Request, db: Session = Depends(get_db)) -> BoardPost:
    if payload.category not in BOARD_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category must be one of {BOARD_CATEGORIES}")

    ip = _client_ip(request)
    enforce_rate_limit(db, ip)
    flag_reason = screen_post(payload.title, payload.description)

    record = BoardPost(
        category=payload.category,
        title=payload.title,
        description=payload.description,
        url=payload.url,
        event_date=payload.event_date,
        submitter_name=payload.submitter_name,
        submitter_email=payload.submitter_email,
        submitter_ip=ip,
        flagged=flag_reason is not None,
        flag_reason=flag_reason,
        approved=False,  # every submission starts hidden -- see README's moderation note
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/board/posts", response_model=list[BoardPostOut])
def list_approved_posts(db: Session = Depends(get_db)) -> list[BoardPost]:
    """The public board -- only ever shows posts an admin has approved.
    Ordered so upcoming events surface first, then everything else by
    recency."""
    return (
        db.query(BoardPost)
        .filter(BoardPost.approved.is_(True))
        .order_by(BoardPost.event_date.is_(None), BoardPost.event_date.asc(), BoardPost.approved_at.desc())
        .all()
    )
