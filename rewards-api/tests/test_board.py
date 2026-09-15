"""The community cork board: public submission, public listing (approved
only), and the admin moderation queue. The core property under test
throughout: nothing a stranger submits is ever visible until an admin
explicitly approves it."""
from tests.conftest import TEST_ADMIN_PASSWORD

VALID_POST = {
    "category": "event",
    "title": "Fall Story Time at the Library",
    "description": "Join us for read-alouds and crafts, Saturdays in October.",
    "url": "https://example.org/storytime",
    "event_date": "2026-10-04",
    "submitter_name": "Jane Parent",
    "submitter_email": "jane@example.com",
}


def test_submitted_post_is_not_publicly_visible(client):
    submit = client.post("/api/board/posts", json=VALID_POST)
    assert submit.status_code == 201

    listing = client.get("/api/board/posts")
    assert listing.status_code == 200
    assert listing.json() == []


def test_public_listing_never_includes_submitter_contact_info(client):
    submit = client.post("/api/board/posts", json=VALID_POST)
    body = submit.json()
    assert "submitter_name" not in body
    assert "submitter_email" not in body


def test_rejects_unknown_category(client):
    r = client.post("/api/board/posts", json={**VALID_POST, "category": "not-a-real-category"})
    assert r.status_code == 422


def test_admin_queue_requires_login(client):
    r = client.get("/api/admin/board/posts")
    assert r.status_code == 401


def test_approve_makes_post_publicly_visible(client):
    submit = client.post("/api/board/posts", json=VALID_POST)
    post_id = submit.json()["id"]

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    approve = client.post(f"/api/admin/board/posts/{post_id}/approve")
    assert approve.status_code == 200

    listing = client.get("/api/board/posts")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["title"] == VALID_POST["title"]


def test_admin_queue_shows_pending_before_approved(client):
    client.post("/api/board/posts", json={**VALID_POST, "title": "Pending One"})
    submit2 = client.post("/api/board/posts", json={**VALID_POST, "title": "Approved One"})
    post2_id = submit2.json()["id"]

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    client.post(f"/api/admin/board/posts/{post2_id}/approve")

    queue = client.get("/api/admin/board/posts").json()
    assert queue[0]["title"] == "Pending One"
    assert queue[0]["approved"] is False
    assert queue[1]["title"] == "Approved One"
    assert queue[1]["approved"] is True


def test_reject_deletes_the_post_and_it_never_becomes_visible(client):
    submit = client.post("/api/board/posts", json=VALID_POST)
    post_id = submit.json()["id"]

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    reject = client.post(f"/api/admin/board/posts/{post_id}/reject")
    assert reject.status_code == 200

    queue = client.get("/api/admin/board/posts").json()
    assert queue == []

    approve_after_reject = client.post(f"/api/admin/board/posts/{post_id}/approve")
    assert approve_after_reject.status_code == 404


def test_clean_post_is_not_flagged(client):
    submit = client.post("/api/board/posts", json=VALID_POST)
    post_id = submit.json()["id"]

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    queue = client.get("/api/admin/board/posts").json()
    row = next(r for r in queue if r["id"] == post_id)
    assert row["flagged"] is False
    assert row["flag_reason"] is None


def test_profane_post_is_flagged_but_still_requires_approval(client):
    submit = client.post("/api/board/posts", json={**VALID_POST, "title": "This is shit"})
    assert submit.status_code == 201  # flagging never blocks submission
    post_id = submit.json()["id"]

    # still hidden from the public board, exactly like any other submission
    assert client.get("/api/board/posts").json() == []

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    queue = client.get("/api/admin/board/posts").json()
    row = next(r for r in queue if r["id"] == post_id)
    assert row["flagged"] is True
    assert "profanity" in row["flag_reason"]


def test_spam_phrase_is_flagged(client):
    submit = client.post("/api/board/posts", json={**VALID_POST, "description": "Buy Now and save big, click here!"})
    post_id = submit.json()["id"]

    client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    row = next(r for r in client.get("/api/admin/board/posts").json() if r["id"] == post_id)
    assert row["flagged"] is True
    assert "spam phrase" in row["flag_reason"]


def test_flag_fields_never_appear_in_the_public_shape(client):
    submit = client.post("/api/board/posts", json={**VALID_POST, "title": "This is shit"})
    body = submit.json()
    assert "flagged" not in body
    assert "flag_reason" not in body


def test_rate_limit_blocks_after_threshold(client):
    from app.services.board_moderation import RATE_LIMIT_PER_HOUR

    for i in range(RATE_LIMIT_PER_HOUR):
        r = client.post("/api/board/posts", json={**VALID_POST, "title": f"Post {i}"})
        assert r.status_code == 201

    over_limit = client.post("/api/board/posts", json={**VALID_POST, "title": "One too many"})
    assert over_limit.status_code == 429
