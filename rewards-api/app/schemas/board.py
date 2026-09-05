from datetime import date, datetime

from pydantic import BaseModel, Field

BOARD_CATEGORIES = ("event", "article", "group", "other")


class BoardPostIn(BaseModel):
    category: str = Field(..., description="One of: " + ", ".join(BOARD_CATEGORIES))
    title: str = Field(..., min_length=1, max_length=140)
    description: str = Field(..., min_length=1, max_length=2000)
    url: str | None = Field(default=None, max_length=500)
    event_date: date | None = None
    submitter_name: str | None = Field(default=None, max_length=120)
    submitter_email: str | None = Field(default=None, max_length=200)


class BoardPostOut(BaseModel):
    """The public shape -- deliberately excludes submitter_name/email,
    which are moderation-only context, never shown on the board itself."""
    id: int
    category: str
    title: str
    description: str
    url: str | None
    event_date: date | None
    approved_at: datetime | None

    model_config = {"from_attributes": True}


class BoardPostAdminOut(BoardPostOut):
    """The admin shape -- adds submitter context and moderation state."""
    approved: bool
    created_at: datetime
    submitter_name: str | None
    submitter_email: str | None
