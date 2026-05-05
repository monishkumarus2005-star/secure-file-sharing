import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from unittest.mock import patch

from app.main import app
from app.database import Base, get_db
from app import models, auth
from app.services import token_blacklist
import fakeredis

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_blacklist.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def mock_redis_globally():
    """Patch redis.from_url globally to use fakeredis for all tests."""
    with patch("redis.from_url") as mocked:
        fake_r = fakeredis.FakeRedis(decode_responses=True)
        mocked.return_value = fake_r
        # We also need to reset the _redis_client in the service for each test
        token_blacklist._redis_client = None
        yield fake_r
        token_blacklist._redis_client = None

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)   # Always start fresh
    Base.metadata.create_all(bind=engine)
    with TestClient(app, base_url="http://testserver") as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="module")
def setup_user(client):
    user_data = {
        "username": "blacklist_user",
        "email": "blacklist@example.com",
        "password": "password123",
        "role": "user"
    }
    client.post("/register", json=user_data)
    return user_data

def test_blacklist_logout_flow(client, setup_user):
    # TEST 2 — Valid token still works before logout
    login_resp = client.post("/auth/login", data={"username": "blacklist_user", "password": "password123"})
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {access_token}"}
    resp_me = client.get("/users/me", headers=headers)
    assert resp_me.status_code == 200
    
    # TEST 1 — Logout invalidates token
    logout_resp = client.post("/auth/logout", json={}, headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully"
    
    # Try calling protected endpoint again
    resp_me_after = client.get("/users/me", headers=headers)
    assert resp_me_after.status_code == 401
    assert resp_me_after.json()["detail"] == "Token has been revoked"

def test_fake_token_rejected(client):
    # TEST 3 — Fake token rejected
    resp = client.get("/users/me", headers={"Authorization": "Bearer faketoken123"})
    assert resp.status_code == 401

def test_redis_direct_verification(client, setup_user):
    # TEST 4 — Redis direct verification
    login_resp = client.post("/auth/login", data={"username": "blacklist_user", "password": "password123"})
    access_token = login_resp.json()["access_token"]
    
    from jose import jwt
    claims = jwt.get_unverified_claims(access_token)
    jti = claims["jti"]
    
    headers = {"Authorization": f"Bearer {access_token}"}
    client.post("/auth/logout", json={}, headers=headers)
    
    r = token_blacklist.get_redis()
    if r:
        assert r.exists(jti) == 1
        assert r.ttl(jti) > 0

def test_graceful_degradation(client, setup_user):
    # TEST 5 — Graceful degradation (Redis down)
    login_resp = client.post("/auth/login", data={"username": "blacklist_user", "password": "password123"})
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    with patch("app.services.token_blacklist.get_redis", return_value=None):
        resp = client.get("/users/me", headers=headers)
        # Should allow through, not 500
        assert resp.status_code == 200

def test_token_reuse_after_logout(client, setup_user):
    # TEST 6 — Token reuse after logout
    login_resp = client.post("/auth/login", data={"username": "blacklist_user", "password": "password123"})
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    client.post("/auth/logout", json={}, headers=headers)
    
    # try 3 times
    for _ in range(3):
        resp = client.get("/users/me", headers=headers)
        assert resp.status_code == 401
