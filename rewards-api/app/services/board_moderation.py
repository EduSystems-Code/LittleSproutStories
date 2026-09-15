"""First-pass screening for the cork board's public submission endpoint --
it takes posts from anyone, no login, by design (the whole point is to be
open). This never blocks or auto-rejects a post: the existing
approve-before-public gate (api/routes/board.py) is what actually keeps
bad content off the board. What this adds:

- `screen_post`: a profanity/spam heuristic that flags a post for the
  admin's attention in the moderation queue -- a hint, not a verdict.
- `enforce_rate_limit`: throttles how many posts one IP can submit, so a
  flood can't outrun a solo admin's ability to review the queue.
"""
import re
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.board_post import BoardPost
from app.time_utils import utcnow

# A short starter list, not a claim of completeness -- worth growing from
# real submissions rather than guessed exhaustively up front. Matched as
# whole words, case-insensitive, so it doesn't trip on substrings.
_BLOCKED_WORDS = {
    "fuck", "shit", "bitch", "asshole", "bastard", "cunt", "dick", "piss",
    "porn", "xxx", "viagra", "cialis", "casino",
}

_SPAM_PHRASES = (
    "click here", "buy now", "act now", "limited time offer",
    "make money fast", "work from home", "risk free",
)

RATE_LIMIT_PER_HOUR = 3
RATE_LIMIT_PER_DAY = 8


def _blocked_word_hit(text: str) -> str | None:
    words = re.findall(r"[a-z']+", text.lower())
    return next((w for w in words if w in _BLOCKED_WORDS), None)


def _spam_phrase_hit(text: str) -> str | None:
    lowered = text.lower()
    return next((p for p in _SPAM_PHRASES if p in lowered), None)


def _url_count(text: str) -> int:
    return len(re.findall(r"https?://", text, flags=re.IGNORECASE))


def _shout_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 20:  # too short for an all-caps read to be meaningful
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def screen_post(title: str, description: str) -> str | None:
    """A short, human-readable flag reason, or None if the post looks
    clean. Never raises -- worst case is an unflagged post, which still
    can't go public without a human approving it."""
    combined = f"{title} {description}"

    word = _blocked_word_hit(combined)
    if word:
        return f"possible profanity ({word!r})"

    phrase = _spam_phrase_hit(combined)
    if phrase:
        return f"spam phrase ({phrase!r})"

    if _url_count(description) >= 3:
        return "multiple links in the description"

    if _shout_ratio(combined) > 0.6:
        return "mostly uppercase"

    return None


def enforce_rate_limit(db: Session, ip: str | None) -> None:
    """429s a submission once an IP has posted too many times recently.
    IP-based, not email-based: submitter_email is optional free text a
    bot can vary for free, but the connection it submits over is the one
    thing it can't shed as cheaply."""
    if not ip:
        return  # can't rate-limit what we can't identify; screening + manual review still apply
    now = utcnow()

    count_hour = db.query(func.count(BoardPost.id)).filter(
        BoardPost.submitter_ip == ip, BoardPost.created_at >= now - timedelta(hours=1)
    ).scalar()
    if count_hour >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many submissions -- please try again later.")

    count_day = db.query(func.count(BoardPost.id)).filter(
        BoardPost.submitter_ip == ip, BoardPost.created_at >= now - timedelta(days=1)
    ).scalar()
    if count_day >= RATE_LIMIT_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many submissions -- please try again later.")
