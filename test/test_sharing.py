"""
test_sharing.py
Tests for signed time-limited file sharing (Task 12).
Uses FastAPI TestClient + SQLite (no live server / Celery required).
"""
import io
import secrets
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app import models, auth

# ─────────────────────────────────────────────
# Test Database Setup
# ─────────────────────────────────────────────
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sharing_task12.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """TestClient with isolated SQLite DB. Celery tasks are mocked."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Mock the Celery task so upload doesn't actually need a worker
    with patch("app.routes.files.process_file_upload") as mock_task, \
         patch("app.services.token_blacklist.get_redis", return_value=None):
        mock_task.delay = MagicMock(return_value=None)
        with TestClient(app, base_url="http://testserver") as c:
            yield c

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def user_a(client):
    resp = client.post("/register", json={
        "username": "share_user_a",
        "email": "share_a@example.com",
        "password": "password123",
        "role": "user"
    })
    assert resp.status_code == 201
    return {"username": "share_user_a", "password": "password123"}


@pytest.fixture(scope="module")
def user_b(client):
    resp = client.post("/register", json={
        "username": "share_user_b",
        "email": "share_b@example.com",
        "password": "password123",
        "role": "user"
    })
    assert resp.status_code == 201
    return {"username": "share_user_b", "password": "password123"}


@pytest.fixture(scope="module")
def auth_a(client, user_a):
    resp = client.post("/auth/login", data=user_a)
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def auth_b(client, user_b):
    resp = client.post("/auth/login", data=user_b)
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def upload_and_complete(client, auth_headers, content=b"Task 12 Shared Content"):
    """Upload a file and manually set its status to 'complete' in the DB."""
    files = {"file": ("sharing_test.txt", io.BytesIO(content), "text/plain")}
    up_resp = client.post("/files/upload", headers=auth_headers, files=files)
    assert up_resp.status_code == 202, f"Upload failed: {up_resp.text}"
    file_id = up_resp.json()["id"]

    # Simulate Celery worker: encrypt file and mark it complete in the DB
    db = TestingSessionLocal()
    try:
        file_record = db.query(models.File).filter(models.File.id == file_id).first()
        assert file_record is not None

        # Encrypt the raw content already on disk and update hash
        import os, hashlib
        from app.encryption import encryption_manager

        with open(file_record.encrypted_path, "rb") as f:
            raw = f.read()

        encrypted = encryption_manager.encrypt_file(raw)
        with open(file_record.encrypted_path, "wb") as f:
            f.write(encrypted)

        file_record.file_hash = hashlib.sha256(raw).hexdigest()
        file_record.processing_status = "complete"
        db.commit()
    finally:
        db.close()

    return file_id, content


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

def test_task12_test1_basic_share_and_download(client, auth_a):
    """TEST 1 — Basic share and download without auth."""
    file_id, original_content = upload_and_complete(client, auth_a)

    # Create share link
    share_resp = client.post(
        f"/files/{file_id}/share",
        headers=auth_a,
        json={"expires_hours": 1, "max_uses": 5}
    )
    assert share_resp.status_code == 200, f"Share creation failed: {share_resp.text}"
    data = share_resp.json()
    assert "token" in data
    token = data["token"]
    share_url = data["share_url"]
    assert share_url.endswith(f"/files/share/{token}")

    # Download WITHOUT auth header
    dl_resp = client.get(share_url)
    assert dl_resp.status_code == 200, f"Download failed: {dl_resp.text}"
    assert "content-disposition" in dl_resp.headers
    assert dl_resp.content == original_content, \
        f"Content mismatch: got {len(dl_resp.content)} bytes, expected {len(original_content)}"

    print(f"\nTEST 1 PASSED — token={token[:8]}..., content_len={len(dl_resp.content)}")


def test_task12_test2_expired_link_returns_410(client, auth_a):
    """TEST 2 — Expired link returns 410."""
    file_id, _ = upload_and_complete(client, auth_a)

    share_resp = client.post(
        f"/files/{file_id}/share",
        headers=auth_a,
        json={"expires_hours": 1}
    )
    assert share_resp.status_code == 200
    token = share_resp.json()["token"]
    share_url = share_resp.json()["share_url"]

    # Manually expire the link in DB
    db = TestingSessionLocal()
    try:
        link = db.query(models.ShareLink).filter(models.ShareLink.token == token).first()
        link.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    exp_resp = client.get(share_url)
    assert exp_resp.status_code == 410, f"Expected 410 Got: {exp_resp.status_code} {exp_resp.text}"
    assert "expired" in exp_resp.json()["detail"].lower()

    print(f"\nTEST 2 PASSED — expired link correctly returns 410")


def test_task12_test3_max_downloads_enforced(client, auth_a):
    """TEST 3 — Max downloads enforced; 3rd download returns 410."""
    file_id, _ = upload_and_complete(client, auth_a)

    share_resp = client.post(
        f"/files/{file_id}/share",
        headers=auth_a,
        json={"expires_hours": 1, "max_uses": 2}
    )
    assert share_resp.status_code == 200
    share_url = share_resp.json()["share_url"]

    r1 = client.get(share_url)
    assert r1.status_code == 200, f"1st download failed: {r1.status_code}"

    r2 = client.get(share_url)
    assert r2.status_code == 200, f"2nd download failed: {r2.status_code}"

    r3 = client.get(share_url)
    assert r3.status_code == 410, f"Expected 410 on 3rd download, got {r3.status_code}"

    print(f"\nTEST 3 PASSED — max_downloads=2 enforced; 3rd attempt returns 410")


def test_task12_test4_revoked_link_returns_410(client, auth_a):
    """TEST 4 — Revoked link returns 410."""
    file_id, _ = upload_and_complete(client, auth_a)

    share_resp = client.post(
        f"/files/{file_id}/share",
        headers=auth_a,
        json={"expires_hours": 1}
    )
    assert share_resp.status_code == 200
    token = share_resp.json()["token"]
    share_url = share_resp.json()["share_url"]

    # Revoke it
    rev_resp = client.delete(f"/files/{file_id}/share/{token}", headers=auth_a)
    assert rev_resp.status_code == 200
    assert rev_resp.json()["message"] == "Share link revoked successfully"

    # Try to use it
    dl_resp = client.get(share_url)
    assert dl_resp.status_code == 410, f"Expected 410, got {dl_resp.status_code}"

    print(f"\nTEST 4 PASSED — revoked link correctly returns 410")


def test_task12_test5_non_owner_cannot_share(client, auth_a, auth_b):
    """TEST 5 — Non-owner gets 403/404 when trying to share."""
    file_id, _ = upload_and_complete(client, auth_a)

    bad_share = client.post(
        f"/files/{file_id}/share",
        headers=auth_b,
        json={"expires_hours": 1}
    )
    assert bad_share.status_code in [403, 404], \
        f"Expected 403/404, got {bad_share.status_code}: {bad_share.text}"

    print(f"\nTEST 5 PASSED — non-owner gets {bad_share.status_code} (access denied)")


def test_task12_test6_audit_log_created(client, auth_a):
    """TEST 6 — Audit log entry created with action='shared_download' and no user_id."""
    file_id, _ = upload_and_complete(client, auth_a)

    share_resp = client.post(
        f"/files/{file_id}/share",
        headers=auth_a,
        json={"expires_hours": 1}
    )
    assert share_resp.status_code == 200
    token = share_resp.json()["token"]
    share_url = share_resp.json()["share_url"]

    # Perform a public download to trigger audit log
    dl_resp = client.get(share_url)
    assert dl_resp.status_code == 200

    # Check audit log in DB
    db = TestingSessionLocal()
    try:
        log = db.query(models.AccessLog).filter(
            models.AccessLog.file_id == file_id,
            models.AccessLog.action_type == "share_download"
        ).first()
        assert log is not None, "No access log entry found for share_download"
        assert log.user_id is None, f"Expected user_id=None, got {log.user_id}"
    finally:
        db.close()

    print(f"\nTEST 6 PASSED — audit log entry created with action='share_download', user_id=None")


def test_task12_test7_list_shares(client, auth_a):
    """TEST 7 — List shares; revoked links are excluded."""
    file_id, _ = upload_and_complete(client, auth_a)

    # Create 2 share links
    s1 = client.post(f"/files/{file_id}/share", headers=auth_a, json={"expires_hours": 1})
    s2 = client.post(f"/files/{file_id}/share", headers=auth_a, json={"expires_hours": 2})
    assert s1.status_code == 200
    assert s2.status_code == 200
    t1 = s1.json()["token"]
    t2 = s2.json()["token"]

    # List → should have both
    list_resp = client.get(f"/files/{file_id}/shares", headers=auth_a)
    assert list_resp.status_code == 200
    shares = list_resp.json()
    tokens = [s["token"] for s in shares]
    assert t1 in tokens, f"Token t1 missing from list: {tokens}"
    assert t2 in tokens, f"Token t2 missing from list: {tokens}"
    assert len(shares) >= 2

    # Revoke t1
    rev = client.delete(f"/files/{file_id}/share/{t1}", headers=auth_a)
    assert rev.status_code == 200

    # List again → t1 should be gone, t2 present
    list_resp2 = client.get(f"/files/{file_id}/shares", headers=auth_a)
    assert list_resp2.status_code == 200
    shares2 = list_resp2.json()
    tokens2 = [s["token"] for s in shares2]
    assert t1 not in tokens2, f"Revoked token t1 still in list"
    assert t2 in tokens2, f"Active token t2 missing from list"

    print(f"\nTEST 7 PASSED — list returns active shares only; revoked excluded")
