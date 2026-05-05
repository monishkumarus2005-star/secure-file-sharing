import requests
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
ADMIN_USER = {"username": "admin", "password": "AdminPassword123!"} # Default test admin
TEST_USER = {"username": "testuser_smoke", "password": "TestPassword123!", "email": "smoke@example.com"}

def setup_user():
    print(f"[*] Setting up test user: {TEST_USER['username']}")
    # Try register
    resp = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
    if resp.status_code not in [201, 400]: # 400 if already exists
        print(f"[!] Setup failed: {resp.text}")
        return None
    
    # Login
    resp = requests.post(f"{BASE_URL}/auth/token", data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    })
    if resp.status_code != 200:
        print(f"[!] Login failed: {resp.text}")
        return None
    return resp.json()["access_token"]

def test_sharing_v2(token):
    print("\n--- Testing Task 12: Redesigned Sharing Lifecycle ---")
    
    # 1. Upload a file
    print("[*] Uploading test file...")
    files = {'file': ('smoke.txt', b'Hello Smoke Test', 'text/plain')}
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/files/upload", files=files, headers=headers)
    if resp.status_code != 202:
        print(f"[!] Upload failed: {resp.text}")
        return False
    file_id = resp.json()["file_id"]
    
    # Wait for processing
    print("[*] Waiting for encryption...")
    time.sleep(2)
    
    # 2. Create share link (max_uses=2)
    print("[*] Creating share link (max_uses=2)...")
    share_data = {"expires_hours": 1, "max_uses": 2}
    resp = requests.post(f"{BASE_URL}/files/{file_id}/share", json=share_data, headers=headers)
    if resp.status_code != 200:
        print(f"[!] Share link creation failed: {resp.text}")
        return False
    
    share_token = resp.json()["token"]
    share_url = resp.json()["share_url"]
    print(f"[+] Share link created: {share_url}")
    
    # 3. Download 1 (Success)
    print("[*] Download 1 (expect 200)...")
    resp = requests.get(f"{BASE_URL}/files/share/{share_token}")
    if resp.status_code != 200:
        print(f"[!] Download 1 failed: {resp.status_code}")
        return False
    print("[+] Download 1 success")
    
    # 4. Download 2 (Success)
    print("[*] Download 2 (expect 200)...")
    resp = requests.get(f"{BASE_URL}/files/share/{share_token}")
    if resp.status_code != 200:
        print(f"[!] Download 2 failed: {resp.status_code}")
        return False
    print("[+] Download 2 success")
    
    # 5. Download 3 (Failure - 410 Gone)
    print("[*] Download 3 (expect 410)...")
    resp = requests.get(f"{BASE_URL}/files/share/{share_token}")
    if resp.status_code != 410:
        print(f"[!] Download 3 did not return 410: {resp.status_code}")
        return False
    print("[+] Download 3 correctly blocked (410 Gone)")
    
    return True

def test_pagination_v2(token):
    print("\n--- Testing Task 16+17: Pagination and Search ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Request files list
    print("[*] Fetching file list...")
    resp = requests.get(f"{BASE_URL}/files/?page=1&limit=5", headers=headers)
    if resp.status_code != 200:
        print(f"[!] Pagination failed: {resp.text}")
        return False
    
    data = resp.json()
    print(f"[+] Total files: {data['total']}")
    print(f"[+] Current page: {data['page']}/{data['pages']}")
    
    if "files" not in data or not isinstance(data["files"], list):
        print("[!] Response missing files list")
        return False
        
    # Search check
    print("[*] Testing search for 'smoke'...")
    resp = requests.get(f"{BASE_URL}/files/?search=smoke", headers=headers)
    search_data = resp.json()
    print(f"[+] Found {search_data['total']} files matching 'smoke'")
    
    return True

if __name__ == "__main__":
    print("=== Secure File Sharing System: Smoke Test Suite ===")
    token = setup_user()
    if not token:
        print("[!] Could not obtain auth token. Is the server running at http://localhost:8000?")
        sys.exit(1)
        
    s1 = test_sharing_v2(token)
    s2 = test_pagination_v2(token)
    
    print("\n--- Summary ---")
    print(f"Task 12 (Sharing): {'PASSED' if s1 else 'FAILED'}")
    print(f"Task 16/17 (Pagination): {'PASSED' if s2 else 'FAILED'}")
    
    if s1 and s2:
        print("\n[SUCCESS] All smoke tests passed!")
    else:
        print("\n[FAILURE] Some smoke tests failed.")
        sys.exit(1)
