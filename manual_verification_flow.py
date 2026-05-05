import httpx
import json
import time
from fastapi.testclient import TestClient
from unittest.mock import patch
import fakeredis

# Import the app and dependencies
from app.main import app
from app.database import Base, engine, get_db
from app.services import token_blacklist
from app import models, auth

# Setup a clean test database and mock redis
SQLALCHEMY_DATABASE_URL = "sqlite:///./manual_verify_flow.db"
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def run_manual_verification():
    print("--- STARTING MANUAL VERIFICATION FLOW (Simulated with fakeredis) ---")
    
    # 1. Setup Redis Mock
    fake_r = fakeredis.FakeRedis(decode_responses=True)
    server = fakeredis.FakeServer()
    
    # Patch the service to use our fake redis
    token_blacklist._redis_client = fake_r
    
    with patch("redis.from_url", return_value=fake_r):
        # Setup DB tables
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        
        with TestClient(app) as client:
            # 2. Register a test user
            print("\\n[1] Registering user...")
            register_resp = client.post("/register", json={
                "username": "verify_user",
                "email": "verify@example.com",
                "password": "Password123!",
                "role": "user"
            })
            assert register_resp.status_code == 201
            print("Successfully registered verify_user.")
            
            # 3. POST /auth/login -> save token
            print("\\n[2] Logging in...")
            login_resp = client.post("/auth/login", data={"username": "verify_user", "password": "Password123!"})
            assert login_resp.status_code == 200
            tokens = login_resp.json()
            access_token = tokens["access_token"]
            print(f"Login successful. Access Token captured.")
            
            # Extract jti for redis check
            from jose import jwt
            claims = jwt.get_unverified_claims(access_token)
            jti = claims["jti"]
            print(f"Captured token JTI: {jti}")
            
            # 4. Confirm protected endpoint works before logout
            print("\\n[3] Verifying access token works (GET /users/me)...")
            headers = {"Authorization": f"Bearer {access_token}"}
            me_resp = client.get("/users/me", headers=headers)
            assert me_resp.status_code == 200
            print(f"Access granted. User: {me_resp.json()['username']}")
            
            # 5. POST /auth/logout with that token
            print("\\n[4] Logging out (POST /auth/logout)...")
            logout_resp = client.post("/auth/logout", json={}, headers=headers)
            assert logout_resp.status_code == 200
            print("Logout successful.")
            
            # 6. redis-cli keys "*" -> jti should appear
            print("\\n[5] Checking Redis state (Simulated redis-cli keys '*')...")
            keys = fake_r.keys("*")
            print(f"Keys in Redis: {keys}")
            if jti in keys:
                print(f"SUCCESS: JTI {jti} found in Redis blacklist.")
            else:
                print(f"FAILURE: JTI {jti} NOT found in Redis.")
                
            # 7. GET /files with that token -> should return 401
            print("\\n[6] Verifying token rejection (GET /files)...")
            files_resp = client.get("/files", headers=headers)
            print(f"Response Status: {files_resp.status_code}")
            if files_resp.status_code == 401:
                print(f"SUCCESS: Token rejected correctly. Detail: {files_resp.json()['detail']}")
            else:
                print(f"FAILURE: Token was NOT rejected (Return code {files_resp.status_code}).")
                
    print("\\n--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    run_manual_verification()
