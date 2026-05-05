"""
Task 16+17 - Pagination and Search Tests
"""
import sys
import types
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out the `magic` C-extension BEFORE any app code is imported.
# This prevents ImportError: failed to find libmagic on Windows hosts.
# ---------------------------------------------------------------------------
_magic_stub = types.ModuleType("magic")
def _fake_from_buffer(buf: bytes, mime: bool = True) -> str:
    # Just return text/plain or match extensions for the mock
    return "text/plain"
_magic_stub.from_buffer = _fake_from_buffer
sys.modules.setdefault("magic", _magic_stub)

# ---------------------------------------------------------------------------
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta
import io
import math
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models, auth, schemas

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def client():
    # Use StaticPool to keep the memory DB alive across multiple connections
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    
    # Mock the Celery task and Redis to avoid hangs
    with patch("app.routes.files.process_file_upload") as mock_task:
        mock_task.delay = MagicMock(return_value=None)
        with TestClient(app, base_url="http://testserver") as c:
            yield c
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="module")
def tokens(client):
    # Register and login Admin
    client.post("/register", json={
        "username": "admin_user", "email": "admin@example.com", "password": "password123", "role": "admin"
    })
    resp_admin = client.post("/auth/login", data={"username": "admin_user", "password": "password123"})
    admin_token = resp_admin.json()["access_token"]

    # Register and login Normal User
    client.post("/register", json={
        "username": "normal_user", "email": "user@example.com", "password": "password123", "role": "user"
    })
    resp_user = client.post("/auth/login", data={"username": "normal_user", "password": "password123"})
    user_token = resp_user.json()["access_token"]

    return {
        "admin": admin_token,
        "user": user_token
    }

def test_pagination_and_search_logic(client, tokens):
    user_headers = {"Authorization": f"Bearer {tokens['user']}"}
    
    # 1. Upload 5 files with distinct names
    filenames = ["pagination_test_apple.txt", "pagination_test_banana.txt", 
                 "pagination_test_cherry.txt", "pagination_test_date.txt", 
                 "pagination_test_elderberry.txt"]
    for fname in filenames:
        resp = client.post(
            "/files/upload",
            files={"file": (fname, io.BytesIO(b"content"), "text/plain")},
            headers=user_headers
        )
        assert resp.status_code == 202

    # 2. Verify all files listed
    resp = client.get("/files/", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["files"]) == 5
    assert data["pages"] == 1

    # 3. Test Pagination (Limit = 2)
    resp = client.get("/files/", params={"page": 1, "limit": 2}, headers=user_headers)
    assert resp.status_code == 200
    p1_data = resp.json()
    assert len(p1_data["files"]) == 2
    assert p1_data["total"] == 5
    assert p1_data["pages"] == 3

    resp = client.get("/files/", params={"page": 2, "limit": 2}, headers=user_headers)
    assert resp.status_code == 200
    p2_data = resp.json()
    assert len(p2_data["files"]) == 2
    assert p2_data["files"][0]["id"] != p1_data["files"][0]["id"]

    # 4. Test Search (Case-Insensitive)
    resp = client.get("/files/", params={"search": "BANANA"}, headers=user_headers)
    assert resp.status_code == 200
    search_data = resp.json()
    assert search_data["total"] == 1
    assert "banana" in search_data["files"][0]["filename"].lower()

    # 5. Test Date Filtering
    # Since they were all uploaded today, from_date=today and to_date=today should show 5
    today_str = date.today().isoformat()
    resp = client.get("/files/", params={"from_date": today_str, "to_date": today_str}, headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 5

    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
    resp = client.get("/files/", params={"from_date": tomorrow_str}, headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 6. Test Admin show_deleted
    # Regular user deletes their file
    file_id_to_delete = data["files"][0]["id"]
    client.delete(f"/files/{file_id_to_delete}", headers=user_headers)
    
    # User listing should show 4
    resp = client.get("/files/", headers=user_headers)
    assert resp.json()["total"] == 4
    
    # Non-admin requesting show_deleted=true should still see 4
    resp = client.get("/files/", params={"show_deleted": True}, headers=user_headers)
    assert resp.json()["total"] == 4
    
    # Admin context (Upload and delete their own file)
    admin_headers = {"Authorization": f"Bearer {tokens['admin']}"}
    client.post(
        "/files/upload",
        files={"file": ("admin_only_file.txt", io.BytesIO(b"admin content"), "text/plain")},
        headers=admin_headers
    )
    # Get ID
    resp = client.get("/files/", headers=admin_headers)
    assert resp.status_code == 200
    admin_file_id = resp.json()["files"][0]["id"]
    
    # Delete it
    client.delete(f"/files/{admin_file_id}", headers=admin_headers)
    
    # Admin default listing: 0 (since they only see their own active files)
    resp = client.get("/files/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    
    # Admin show_deleted=true: 1 (they see their own deleted file)
    resp = client.get("/files/", params={"show_deleted": True}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
