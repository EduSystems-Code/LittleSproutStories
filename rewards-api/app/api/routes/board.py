from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.board_post import BoardPost
from app.schemas.board import BOARD_CATEGORIES, BoardPostIn, BoardPostOut

router = APIRouter()


@router.post("/board/posts", response_model=BoardPostOut, status_code=201)
def submit_post(payload: BoardPostIn, db: Session = Depends(get_db)) -> BoardPost:
    if payload.category not in BOARD_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category must be one of {BOARD_CATEGORIES}")
    record = BoardPost(
        category=payload.category,
        title=payload.title,
        description=payload.description,
        url=payload.url,
        event_date=payload.event_date,
        submitter_name=payload.submitter_name,
        submitter_email=payload.submitter_email,
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
