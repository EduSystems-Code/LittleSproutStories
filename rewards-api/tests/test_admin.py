"""Admin auth + dashboard. Password-gate correctness matters more here
than almost anywhere else in this app -- it's the only thing standing
between the public internet and a list of real mailing addresses."""
from tests.conftest import TEST_ADMIN_PASSWORD, make_paid_order


def test_wrong_password_rejected(client):
    r = client.post("/api/admin/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_requests_list_requires_login(client):
    r = client.get("/api/admin/requests")
    assert r.status_code == 401


def test_login_then_list_and_mark_sent(client, db_session):
    order = make_paid_order(db_session, stripe_checkout_session_id="cs_admin_flow")
    submit = client.post(
        "/api/requests",
        json={
            "token": order.token,
            "recipient_name": "Jane Parent",
            "address_line1": "123 Main St",
            "city": "Baltimore",
            "state": "MD",
            "postal_code": "21201",
        },
    )
    assert submit.status_code == 201
    request_id = submit.json()["id"]

    login = client.post("/api/admin/login", json={"password": TEST_ADMIN_PASSWORD})
    assert login.status_code == 200

    listing = client.get("/api/admin/requests")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["sent_at"] is None

    mark = client.post(f"/api/admin/requests/{request_id}/mark-sent")
    assert mark.status_code == 200

    listing2 = client.get("/api/admin/requests")
    assert listing2.json()[0]["sent_at"] is not None
