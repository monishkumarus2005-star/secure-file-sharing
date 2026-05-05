import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta
import io
import math
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import Base, get_db
from app import models, auth, schemas

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_pagination.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def client():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Mock the Celery task and Redis to avoid hangs
    with patch("app.routes.files.process_file_upload") as mock_task:
        mock_task.delay = MagicMock(return_value=None)
        with TestClient(app, base_url="http://testserver") as c:
            yield c
    
    Base.metadata.drop_all(bind=engine)
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

def test_pagination_and_search(client, tokens):
    user_headers = {"Authorization": f"Bearer {tokens['user']}"}
    
    # 1. Upload 5 files with different names
    filenames = ["apple.txt", "banana.pdf", "cherry.docx", "date.xlsx", "elderberry.jpg"]
    for fname in filenames:
        resp = client.post(
            "/files/upload",
            files={"file": (fname, io.BytesIO(b"content"), "text/plain")},
            headers=user_headers
        )
        assert resp.status_code == 202

    # 2. Test Basic Listing
    resp = client.get("/files/", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["files"]) == 5
    assert data["page"] == 1
    assert data["limit"] == 20
    assert data["pages"] == 1

    # 3. Test Pagination (Limit=2)
    resp = client.get("/files/", params={"page": 1, "limit": 2}, headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["files"]) == 2
    assert data["page"] == 1
    assert data["pages"] == 3

    resp = client.get("/files/", params={"page": 3, "limit": 2}, headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["files"]) == 1
    assert data["page"] == 3

    # 4. Test Search (Case-Insensitive)
    resp = client.get("/files/", params={"search": "ANANA"}, headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["files"][0]["filename"] == "banana.pdf"

    # 5. Test Date Filtering (from_date/to_date)
    today = date.today().isoformat()
    resp = client.get("/files/", params={"from_date": today, "to_date": today}, headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 5

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    resp = client.get("/files/", params={"from_date": tomorrow}, headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 6. Test Admin show_deleted
    resp = client.get("/files/", headers=user_headers)
    file_id = resp.json()["files"][0]["id"]
    
    # Delete a file (soft delete)
    client.delete(f"/files/{file_id}", headers=user_headers)
    
    # User listing should now show 4
    resp = client.get("/files/", headers=user_headers)
    assert resp.json()["total"] == 4
    
    # User requesting show_deleted=True should still see 4 (role enforcement)
    resp = client.get("/files/", params={"show_deleted": True}, headers=user_headers)
    assert resp.json()["total"] == 4
    
    # Admin context
    admin_headers = {"Authorization": f"Bearer {tokens['admin']}"}
    # Admin uploads their own file
    client.post(
        "/files/upload",
        files={"file": ("admin_file.txt", io.BytesIO(b"content"), "text/plain")},
        headers=admin_headers
    )
    
    # Admin deletes their own file
    resp = client.get("/files/", headers=admin_headers)
    admin_file_id = resp.json()["files"][0]["id"]
    client.delete(f"/files/{admin_file_id}", headers=admin_headers)
    
    # Admin listing should show 0 by default
    resp = client.get("/files/", headers=admin_headers)
    assert resp.json()["total"] == 0
    
    # Admin listing with show_deleted=True should show 1
    resp = client.get("/files/", params={"show_deleted": True}, headers=admin_headers)
    assert resp.json()["total"] == 1
