"""All tunables and secrets live here, read from .env -- nothing
Stripe- or admin-auth-specific is hardcoded anywhere else.

Stripe keys and the admin password are optional at startup (rather than
required, Pydantic-validated-on-boot fields) so the app can come up and
pass a health check before Stripe's business-verification (KYB) step is
done -- each feature that actually needs one of these checks for it at
the point of use and fails with a clear, specific message instead of the
whole app refusing to start. See Chegga/backend/app/config.py for the
same pattern this is deliberately mirroring.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Blank until a real Stripe payments account is connected. A completed
    # Checkout payment is both the purchase AND the COPPA verifiable-
    # parental-consent step (the FTC's own "check a form of payment"
    # method) -- there is no separate Identity/KYB step in this flow.
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None

    # Printify handles every made-to-order Shop item (see app/products.py --
    # the reward box is the one exception, hand-kitted via a 3PL and marked
    # sent from the admin dashboard). Both blank until a real Printify
    # account exists: order submission still succeeds and the row falls
    # back to manual handling, exactly like Stripe being unconfigured.
    # Personal Access Token from Printify -> My Account -> Connections ->
    # API tokens (order-write scope), NOT a Shopify token.
    printify_api_token: str | None = None
    printify_shop_id: str | None = None

    # The reward box: poster, certificate, sticker sheet, bookmark, button.
    # Priced to cover item cost (~$1.50-2.65), packaging (~$0.30), postage
    # (~$2-5 padded mailer), and Stripe's processing fee (~$0.59 on $10) --
    # real vendor quotes still needed before this ships for real, not
    # invented as a final number.
    reward_box_price_cents: int = 1000

    # Single shared password for the one admin (solo operation -- no
    # per-user accounts needed). Session auth via a signed cookie
    # (itsdangerous), not a database-backed session table.
    admin_password: str | None = None
    admin_session_secret: str = "dev-only-change-me"
    # The admin session cookie is Secure (HTTPS-only) by default -- correct
    # and required for the real deployment. Only flip this off for local
    # dev/testing over plain http://localhost, where a Secure cookie is
    # silently refused by the browser/client, not sent at all.
    admin_cookie_secure: bool = True

    # How long a fulfilled request's mailing address is kept before being
    # deleted -- see services/retention.py. Matches the plan's "don't hold
    # what we don't need any longer than necessary" commitment.
    retention_days_after_sent: int = 90

    # SQLite by default for zero-friction local dev. The deployed service
    # points this at a managed Postgres instead (Render's free tier wipes
    # the filesystem on every deploy, so a SQLite file there loses every
    # pending mailing address). Any Postgres URL works -- see
    # `sqlalchemy_url` for the driver normalisation.
    database_url: str = "sqlite:///./data/rewards.db"

    # Which origin(s) may call this API -- the live LittleSprout Stories
    # site. Kept a plain list here (not hardcoded in main.py) so a local
    # dev origin can be added via .env without touching code.
    allowed_origins: str = "https://edusystems-code.github.io"

    # Where Stripe sends the buyer back after they finish (or cancel)
    # Checkout -- the token is appended as a query param so the page knows
    # which order to poll (see /checkout/status). The reward box returns to
    # rewards_page_url; every other product (app/products.py) returns to
    # shop_page_url instead.
    rewards_page_url: str = "https://edusystems-code.github.io/LittleSproutStories/rewards.html"
    shop_page_url: str = "https://edusystems-code.github.io/LittleSproutStories/shop.html"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """`database_url` normalised for SQLAlchemy 2.x. A managed Postgres
        provider typically hands back a `postgres://` or bare
        `postgresql://` URL; SQLAlchemy 2 rejects the first outright and
        defaults the second to psycopg2 (not installed -- we pin psycopg
        v3). Rewrite both to `postgresql+psycopg://`. SQLite, and any URL
        that already names a driver, pass through untouched."""
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
