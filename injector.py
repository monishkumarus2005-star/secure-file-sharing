import requests

# Replace with your actual username and password
USERNAME = "monish"
PASSWORD = "monish123"

# Login first to get token
resp = requests.post(
    "http://localhost:8000/login",
    data={"username": USERNAME, "password": PASSWORD}
)

print(f"Login status: {resp.status_code}")
print(f"Response: {resp.json()}")

if resp.status_code != 200:
    print("Login failed! Check your credentials.")
    exit(1)

token = resp.json()["access_token"]
print(f"Got token: {token[:20]}...")

# Rapidly download a file to trigger anomaly detection
# Using file ID 1 (UHV.docx from your dashboard)
FILE_ID = 54


headers = {"Authorization": f"Bearer {token}"}
for i in range(15):  # More than 10 to trigger anomaly
    r = r = requests.get(f"http://localhost:8000/files/download/{FILE_ID}", headers=headers)
    print(f"Download {i+1}: {r.status_code}")

print("\nDone! Check the dashboard for anomaly detection.")