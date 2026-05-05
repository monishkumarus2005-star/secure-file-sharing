import pytest
import time
import os
import requests
from app.database import SessionLocal
from app.models import File, User
from app.config import settings

# Note: This test assumes the backend, redis, and worker are running.
# In a CI environment, we would use mocks or a test docker-compose.
# For this verification, we'll try to hit the running API.

BASE_URL = "http://localhost:8000"  # Adjust if needed

@pytest.fixture
def auth_header():
    # Login and get token
    # This assumes a test user exists or we create one
    db = SessionLocal()
    user = db.query(User).filter(User.username == "testuser").first()
    if not user:
        # Create test user if not exists (simplified)
        from app.auth import get_password_hash
        user = User(username="testuser", email="test@example.com", hashed_password=get_password_hash("password123"))
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": "testuser", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_upload_and_process_flow(auth_header):
    # Upload a file
    test_file_path = "test_upload.txt"
    content = b"Hello, this is a test file for Celery background processing."
    with open(test_file_path, "wb") as f:
        f.write(content)
    
    try:
        with open(test_file_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/files/upload",
                headers=auth_header,
                files={"file": ("test_upload.txt", f, "text/plain")}
            )
        
        assert response.status_code == 202
        data = response.json()
        file_id = data["id"]
        assert data["status"] == "pending"
        
        # Poll status
        max_retries = 30
        status = "pending"
        for _ in range(max_retries):
            time.sleep(2)
            status_response = requests.get(f"{BASE_URL}/files/{file_id}/status", headers=auth_header)
            assert status_response.status_code == 200
            status = status_response.json()["status"]
            if status in ["complete", "failed"]:
                break
        
        assert status == "complete"
        
        # Verify file on disk is encrypted
        # We need to find the file path from DB
        db = SessionLocal()
        file_rec = db.query(File).filter(File.id == file_id).first()
        encrypted_path = file_rec.encrypted_path
        db.close()
        
        with open(encrypted_path, "rb") as f:
            disk_content = f.read()
        
        assert disk_content != content  # Should be encrypted
        
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    # If running manually
    pass
