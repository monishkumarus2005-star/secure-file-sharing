"""
Task 2 - File Type/Size Validation Tests
Tests: size limit (50MB), magic-byte whitelist, extension mismatch, empty files.
Magic is mocked at the sys.modules level so no libmagic DLL is needed on Windows.
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
    if buf[:2] == b"MZ":
        return "application/x-dosexec"
    if buf[:4] == b"%PDF":
        return "application/pdf"
    if buf[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if buf[:4] == b"\x89PNG":
        return "image/png"
    if b"id,name" in buf:
        return "text/csv"
    return "text/plain"

_magic_stub.from_buffer = _fake_from_buffer
sys.modules.setdefault("magic", _magic_stub)

# ---------------------------------------------------------------------------
# Now it is safe to import app code.
# ---------------------------------------------------------------------------
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
    Base.metadata.create_all(bind=engine)

    with patch("app.routes.files.process_file_upload") as mock_task:
        mock_task.delay = MagicMock(return_value=None)
        with TestClient(app, base_url="http://testserver") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def user_token(client):
    client.post("/register", json={
        "username": "validator_user",
        "email": "val@example.com",
        "password": "password123",
        "role": "user",
    })
    resp = client.post("/auth/login", data={"username": "validator_user", "password": "password123"})
    return resp.json()["access_token"]


def test_file_validation_flows(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    # --- TEST 1: valid PDF → 202 ---
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Test) >>\nendobj"
    resp = client.post(
        "/files/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 202, f"PDF upload failed: {resp.text}"

    # --- TEST 2: file > 50 MB → 413 ---
    oversized = b"0" * (50 * 1024 * 1024 + 1)
    resp = client.post(
        "/files/upload",
        files={"file": ("large.txt", io.BytesIO(oversized), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 413, f"Expected 413, got {resp.status_code}"

    # --- TEST 3: .jpg that is secretly an EXE (MZ magic) → 400 ---
    fake_exe = b"MZ" + b"\x00" * 100
    resp = client.post(
        "/files/upload",
        files={"file": ("fake.jpg", io.BytesIO(fake_exe), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "application/x-dosexec" in resp.json()["detail"]

    # --- TEST 4: .exe uploaded directly → 400 ---
    resp = client.post(
        "/files/upload",
        files={"file": ("malware.exe", io.BytesIO(fake_exe), "application/x-msdownload")},
        headers=headers,
    )
    assert resp.status_code == 400

    # --- TEST 5: 0-byte file → 400 ---
    resp = client.post(
        "/files/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400

    # --- TEST 6: each whitelisted type → 202 ---
    allowed_cases = [
        ("doc.pdf",   b"%PDF-",              "application/pdf"),
        ("image.jpg", b"\xff\xd8\xff",       "image/jpeg"),
        ("image.png", b"\x89PNG\r\n\x1a\n",  "image/png"),
        ("data.txt",  b"Hello world",        "text/plain"),
        ("data.csv",  b"id,name\n1,test",    "text/csv"),
    ]
    for fname, content, mtype in allowed_cases:
        resp = client.post(
            "/files/upload",
            files={"file": (fname, io.BytesIO(content), mtype)},
            headers=headers,
        )
        assert resp.status_code == 202, f"Expected 202 for {fname}, got {resp.status_code}: {resp.text}"

    # --- TEST 7: no extension → 400 ---
    resp = client.post(
        "/files/upload",
        files={"file": ("no_extension", io.BytesIO(b"content"), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "no extension" in resp.json()["detail"].lower()
