import httpx
import json
import time
from fastapi.testclient import TestClient
import redis

# Import the app and dependencies
from app.main import app
from app.database import Base, engine, get_db
from app.services import token_blacklist
from app import models, auth
from app.config import settings

# Setup a clean test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./manual_verify_real.db"
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
    print("--- STARTING MANUAL VERIFICATION FLOW (REAL REDIS) ---")
    print(f"Connecting to Redis at: {settings.REDIS_URL}")
    
    # Ensure service uses real settings
    token_blacklist._redis_client = None 
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        r.ping()
        print("Redis Connection: SUCCESS (PONG)")
    except Exception as e:
        print(f"Redis Connection: FAILED - {e}")
        return

    # Clear existing data in Redis (optional but good for clean test)
    r.flushall()
    print("Redis state flushed for clean test.")

    # Setup DB tables
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    with TestClient(app) as client:
        # 1. Register a test user
        print("\\n[1] Registering user...")
        register_resp = client.post("/register", json={
            "username": "real_redis_user",
            "email": "real@example.com",
            "password": "Password123!",
            "role": "user"
        })
        assert register_resp.status_code == 201
        print("Successfully registered real_redis_user.")
        
        # 2. POST /auth/login -> save token
        print("\\n[2] Logging in...")
        login_resp = client.post("/auth/login", data={"username": "real_redis_user", "password": "Password123!"})
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        print(f"Login successful. Access Token captured.")
        
        # Extract jti for redis check
        from jose import jwt
        claims = jwt.get_unverified_claims(access_token)
        jti = claims["jti"]
        print(f"Captured token JTI: {jti}")
        
        # 3. Confirm protected endpoint works before logout
        print("\\n[3] Verifying access token works (GET /users/me)...")
        headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = client.get("/users/me", headers=headers)
        assert me_resp.status_code == 200
        print(f"Access granted. User: {me_resp.json()['username']}")
        
        # 4. POST /auth/logout with that token
        print("\\n[4] Logging out (POST /auth/logout)...")
        logout_resp = client.post("/auth/logout", json={}, headers=headers)
        assert logout_resp.status_code == 200
        print("Logout successful.")
        
        # 5. Check Redis keys
        print("\\n[5] Checking REAL Redis state...")
        import subprocess
        try:
            # We use docker exec to run redis-cli keys "*" as requested
            res = subprocess.run(['docker', 'exec', 'minorprojet3-redis-1', 'redis-cli', 'keys', '*'], capture_output=True, text=True)
            keys = res.stdout.strip().split('\\n')
            print(f"Keys in Redis: {keys}")
            if jti in keys:
                print(f"SUCCESS: JTI {jti} found in Redis blacklist.")
            else:
                print(f"FAILURE: JTI {jti} NOT found in Redis.")
        except Exception as e:
            print(f"Could not run docker exec: {e}")
            # fall back to python redis client
            keys = r.keys("*")
            print(f"Keys (via Python): {keys}")
            if jti in keys:
                print(f"SUCCESS: JTI {jti} found in Redis blacklist.")

        # 6. GET /files with that token -> should return 401
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
