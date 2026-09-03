# Little Sprout Rewards

> **Part of the LittleSprout Stories repo.** This was previously the
> standalone private repo `EduSystems-Code/LittleSprout-Rewards`;
> consolidated into the main (public) site repo on 2026-09-03 as
> `rewards-api/`. It still deploys as its **own** Render web service from
> this subdirectory (`rootDir: rewards-api`, see `render.yaml`) — GitHub
> Pages serves the static site from the repo root and ignores this folder.
> Nothing sensitive is committed here: `.env`, keys, and the SQLite DB are
> all git-ignored and always were.

The backend for Little Sprout Stories' "finish all 14 books" reward
box, the general merch Shop (t-shirt, cap, water bottle), and the
community cork board (events, articles, groups). Mirrors
`Chegga/backend`'s own stack (FastAPI + SQLAlchemy + Alembic +
SQLite) rather than introducing an unfamiliar one.

## Why this exists

Little Sprout Stories itself is a 100% static site with an explicit
"we collect nothing" privacy promise. This is the one deliberate
exception: buying anything (the reward box, or a Shop item) asks for
a name and mailing address, stored here just long enough to mail it,
then scrubbed.

Every purchasable item lives in one catalog, `app/products.py`, and
shares one Checkout/fulfillment pipeline (`Order` + `Fulfillment`) --
adding a new product is a catalog entry, not a new integration. The
reward box is reached only through the badge shelf's "finished all 14
books" CTA and is never listed on the general Shop page; everything
else in the catalog (`shop_visible: True`) shows up there.

**Why a real charge instead of a free reward with separate consent
verification:** a completed Stripe Checkout payment is itself an
FTC-approved method of verifiable parental consent under COPPA (the
FTC's own "check a form of payment, such as a credit card" method) —
so paying for the box does double duty as the purchase and the
consent step, without a separate Stripe Identity (ID+selfie) check on
top. That's both cheaper (Identity runs ~$1–1.50/attempt, charged
regardless of outcome) and a stronger anti-abuse barrier (a bot can't
supply a real card that clears a $10 charge), which is what actually
made a free, unlimited version of this unworkable at scale.

## Stack

- FastAPI + SQLAlchemy 2.0 + Alembic + SQLite
- Stripe Checkout for payment (and, by extension, parental consent)
- A single-shared-password admin session (signed cookie via
  `itsdangerous`) — no user accounts, matches solo operation

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env     # fill in ADMIN_PASSWORD at minimum
alembic upgrade head
uvicorn app.main:app --reload
```

`STRIPE_API_KEY`/`STRIPE_WEBHOOK_SECRET` stay blank until a real
Stripe payments account is connected — the app runs fine without
them; `/checkout/start` and the webhook just return a clear 503 until
they're set.

## Endpoints

| Route | What it does |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/products` | The Shop's catalog (name, price, description, size/color variants if any) — excludes the reward box, which isn't a Shop item |
| `POST /api/checkout/start` | Begins a Stripe Checkout session for a given `product_id` (defaults to `reward_box`), returns the hosted checkout URL |
| `GET /api/checkout/status` | Polled by the frontend after Stripe redirects back — the webhook is async, so this covers the race where the buyer lands back before it's processed; also returns which product/variants apply |
| `POST /api/webhooks/stripe` | Stripe's own signed callback — the only thing allowed to mark an order paid |
| `POST /api/requests` | Submits a mailing address (and size/color `variant`, if applicable), only accepted against an already-paid, not-yet-consumed order token |
| `POST /api/admin/login` | Single shared password → session cookie |
| `GET /api/admin/requests` | Pending (and recently sent) requests, each labeled with what product it's for — sweeps expired ones first (see retention below) |
| `POST /api/admin/requests/{id}/mark-sent` | Marks a request fulfilled |
| `POST /api/board/posts` | Public submission to the cork board — starts hidden (`approved=False`) until a moderator reviews it |
| `GET /api/board/posts` | The public board — only ever returns approved posts, never submitter contact info |
| `GET /api/admin/board/posts` | The moderation queue — pending posts first, includes submitter name/email for context |
| `POST /api/admin/board/posts/{id}/approve` | Makes a post publicly visible |
| `POST /api/admin/board/posts/{id}/reject` | Deletes a post outright — there's no "rejected" state to keep, and an unapproved submission carries an email that shouldn't linger once declined |

## Moderation

Every cork-board submission starts hidden. Nothing appears on the
public board (`GET /api/board/posts`) until an admin explicitly
approves it from the queue (`GET /api/admin/board/posts`) — this was
a deliberate choice over "live immediately, moderate after," since the
board accepts open public submissions on a children's site and a bad
post being visible even briefly isn't an acceptable tradeoff for
faster-feeling content.

## Data retention

A request's mailing-address fields are scrubbed (not the row —
kept for count/audit purposes) `RETENTION_DAYS_AFTER_SENT` (90 by
default) after it's marked sent. The sweep runs on every admin
dashboard load (`app/services/retention.py`) rather than a scheduled
job — cheap enough at this volume, and correct even if the app has
been asleep (Render's free tier spins down on idle) longer than the
retention window itself.

## Testing

```bash
pytest
```

Every test runs against a fresh in-memory SQLite database (see
`tests/conftest.py`) — never the real `data/rewards.db` file.
Verified directly: real dev-database mtime is unchanged before/after
a full test run.

## Deploying

Render (free tier), matching Chegga's own low-traffic hosting choice.
Free tier spins down on idle and cold-starts (~30-50s) on the first
request after a quiet period — acceptable for a low-volume,
non-urgent form; not something that would be acceptable for a
higher-traffic use case.
