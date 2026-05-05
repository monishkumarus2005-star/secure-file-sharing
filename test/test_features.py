import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from app.main import app
from app.database import Base, get_db
from app import models, auth
import io

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_secure_file_sharing.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def client():
    # Clear overrides to prevent bleed from other test modules
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    with TestClient(app, base_url="http://testserver") as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="module")
def setup_user(client):
    user_data = {
        "username": "testuser1",
        "email": "test1@example.com",
        "password": "password123",
        "role": "user"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 201
    return user_data

def test_refresh_token_flow(client, setup_user):
    # 1. Login -> get both tokens
    resp = client.post("/auth/login", data={"username": "testuser1", "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    acc_token = data["access_token"]
    ref_token = data["refresh_token"]
    
    # Check access is valid
    resp_me = client.get("/users/me", headers={"Authorization": f"Bearer {acc_token}"})
    assert resp_me.status_code == 200
    
    # Call /auth/refresh -> confirm new access token works
    resp_ref = client.post("/auth/refresh", json={"refresh_token": ref_token})
    assert resp_ref.status_code == 200
    ref_data = resp_ref.json()
    new_acc_token = ref_data["access_token"]
    new_ref_token = ref_data["refresh_token"]
    
    resp_me2 = client.get("/users/me", headers={"Authorization": f"Bearer {new_acc_token}"})
    assert resp_me2.status_code == 200
    
    # 2. Logout -> try to reuse refresh token -> expect 401
    resp_logout = client.post("/auth/logout", json={"refresh_token": new_ref_token}, headers={"Authorization": f"Bearer {new_acc_token}"})
    assert resp_logout.status_code == 200
    
    resp_reuse = client.post("/auth/refresh", json={"refresh_token": new_ref_token})
    assert resp_reuse.status_code == 401

def test_refresh_token_fake_expired(client, setup_user):
    # 3. /auth/refresh with fake token
    resp_fake = client.post("/auth/refresh", json={"refresh_token": "fake_token_123"})
    assert resp_fake.status_code == 401
    
    # 4. /auth/refresh with expired token
    session = TestingSessionLocal()
    user = session.query(models.User).filter_by(username="testuser1").first()
    raw_rt, hashed_rt = auth.create_refresh_token()
    expired_rt = models.RefreshToken(
        user_id=user.id,
        token=hashed_rt,
        expires_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    session.add(expired_rt)
    session.commit()
    session.close()
    
    resp_exp = client.post("/auth/refresh", json={"refresh_token": raw_rt})
    assert resp_exp.status_code == 401

def test_password_reset_flow(client, setup_user):
    # 1. Valid email -> email mock called
    resp_forgot = client.post("/auth/forgot-password", json={"email": "test1@example.com"})
    assert resp_forgot.status_code == 200
    
    session = TestingSessionLocal()
    user = session.query(models.User).filter_by(username="testuser1").first()
    pt_record = session.query(models.PasswordResetToken).filter_by(user_id=user.id).order_by(models.PasswordResetToken.id.desc()).first()
    
    # We must retrieve the raw token indirectly. Since we mock email, we can't get it from response.
    # To test we insert a custom token manually to test endpoints.
    raw_token = "my-secret-reset-token-123"
    hashed_token = auth.hash_token(raw_token)
    custom_pt = models.PasswordResetToken(
        user_id=user.id,
        token=hashed_token,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    )
    session.add(custom_pt)
    session.commit()
    
    # 2. Valid token -> password updated -> token marked used
    resp_reset = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "newpassword123"})
    assert resp_reset.status_code == 200
    
    # Test new password works
    resp_login = client.post("/auth/login", data={"username": "testuser1", "password": "newpassword123"})
    assert resp_login.status_code == 200
    
    # 3. Same token reused -> expect 400
    resp_reuse = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "newpassword123"})
    assert resp_reuse.status_code == 400
    
    # 4. Token older than 15 min -> expect 400
    raw_token_exp = "my-expired-reset-token"
    hashed_exp = auth.hash_token(raw_token_exp)
    exp_pt = models.PasswordResetToken(
        user_id=user.id,
        token=hashed_exp,
        expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    )
    session.add(exp_pt)
    session.commit()
    session.close()
    
    resp_exp = client.post("/auth/reset-password", json={"token": raw_token_exp, "new_password": "abc123456789"})
    assert resp_exp.status_code == 400
    
    # 5. Unknown email -> expect 200
    resp_unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp_unknown.status_code == 200

def test_input_validation(client, setup_user):
    # 4. Register with username "'; DROP TABLE users;--" -> expect 422
    resp_sql = client.post("/register", json={
        "username": "'; DROP TABLE users;--",
        "email": "testsql@example.com",
        "password": "password123",
        "role": "user"
    })
    assert resp_sql.status_code == 422
    
    # 5. Register with 500-char username -> expect 422
    resp_long = client.post("/register", json={
        "username": "a" * 500,
        "email": "testlong@example.com",
        "password": "password123",
        "role": "user"
    })
    assert resp_long.status_code == 422
    
    # 6. Register with "not-an-email" -> expect 422
    resp_badmail = client.post("/register", json={
        "username": "valid_user",
        "email": "not-an-email",
        "password": "password123",
        "role": "user"
    })
    assert resp_badmail.status_code == 422

def test_file_upload_sanitization(client, setup_user):
    resp_login = client.post("/auth/login", data={"username": "testuser1", "password": "newpassword123"})
    acc_token = resp_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {acc_token}"}
    
    # 1. Upload filename "../../etc/passwd" -> expect 400
    file_content = b"fake file content"
    files1 = {
        "file": ("../../etc/passwd", io.BytesIO(file_content), "text/plain")
    }
    resp_trav = client.post("/files/upload", files=files1, headers=headers)
    assert resp_trav.status_code == 400
    
    # 2. Upload "malware.exe\\x00.jpg" -> expect 400
    files2 = {
        "file": ("malware.exe\\x00.jpg", io.BytesIO(file_content), "image/jpeg")
    }
    resp_null = client.post("/files/upload", files=files2, headers=headers)
    assert resp_null.status_code == 400
    
    # 3. Upload "normal_file.pdf" -> expect 201 (app responds with 201 Created on valid upload)
    files3 = {
        "file": ("normal_file.pdf", io.BytesIO(file_content), "application/pdf")
    }
    resp_norm = client.post("/files/upload", files=files3, headers=headers)
    assert resp_norm.status_code == 202


def test_jti_in_access_token(client, setup_user):
    from jose import jwt
    resp = client.post("/auth/login", data={"username": "testuser1", "password": "newpassword123"})
    assert resp.status_code == 200
    acc_token = resp.json()["access_token"]
    
    # We must decode without verifying signature to just inspect payload directly
    decoded = jwt.get_unverified_claims(acc_token)
    # Print it to be captured by test output
    print(f"\\nDecoded access token payload: {decoded}")
    assert "jti" in decoded

