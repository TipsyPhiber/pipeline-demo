"""Unit tests: happy paths plus rejection paths.

The rejection tests matter as much as the happy path — they prove the
input-validation controls actually fire, which is the security story.
"""

from fastapi.testclient import TestClient

from app.main import MAX_TEXT_LEN, app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz():
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_transform_happy_path():
    resp = client.post("/transform", json={"text": "Hello", "action": "upper"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "HELLO"}


def test_transform_reverse():
    resp = client.post("/transform", json={"text": "abc", "action": "reverse"})
    assert resp.json() == {"result": "cba"}


def test_transform_rejects_unknown_action():
    # Default-deny: an action outside the allow-list is a 422, not a 200.
    resp = client.post("/transform", json={"text": "hi", "action": "delete_all"})
    assert resp.status_code == 422


def test_transform_rejects_oversized_text():
    resp = client.post(
        "/transform",
        json={"text": "x" * (MAX_TEXT_LEN + 1), "action": "upper"},
    )
    assert resp.status_code == 422


def test_transform_rejects_empty_text():
    resp = client.post("/transform", json={"text": "", "action": "upper"})
    assert resp.status_code == 422
