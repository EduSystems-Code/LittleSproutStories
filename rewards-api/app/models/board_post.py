from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.time_utils import utcnow


class BoardPost(Base):
    """One submission to the community cork board (events, articles,
    Facebook groups, gatherings -- anything a family might want to share
    with other families). Nothing here is public until `approved` is set
    true by an admin -- see api/routes/board.py's public listing, which
    filters on it. No child data involved; the submitter fields describe
    an adult posting on behalf of their family/organization."""

    __tablename__ = "board_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(20))  # event | article | group | other
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Only meaningful for category == "event" -- null otherwise. A date,
    # not a datetime: this is "the gathering is on such-and-such day", not
    # a precise timestamp.
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Who submitted it -- shown to the admin for moderation context only,
    # never displayed on the public board itself.
    submitter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    submitter_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
