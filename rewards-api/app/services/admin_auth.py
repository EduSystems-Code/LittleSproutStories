"""Single-shared-password admin auth via a signed cookie -- no user table,
no per-account login, matching the "solo operation, no user-management
system needed" call in the plan doc. itsdangerous signs the cookie so it
can't be forged without admin_session_secret; there's nothing in it worth
encrypting (just a fixed "is the admin" marker), only worth signing.
"""
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings

COOKIE_NAME = "rewards_admin"
MAX_AGE_SECONDS = 60 * 60 * 12  # 12 hours


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.admin_session_secret, salt="rewards-admin")


def make_session_cookie() -> str:
    return _serializer().dumps({"admin": True})


def check_password(password: str) -> bool:
    settings = get_settings()
    if not settings.admin_password:
        return False
    return password == settings.admin_password


def is_valid_session_cookie(cookie_value: str | None) -> bool:
    if not cookie_value:
        return False
    try:
        data = _serializer().loads(cookie_value, max_age=MAX_AGE_SECONDS)
    except BadSignature:
        return False
    return bool(data.get("admin"))
