import magic
import logging
import os
from fastapi import HTTPException

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

ALLOWED_TYPES = {
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "text/plain": [".txt"],
    "text/csv": [".csv"],
    "application/vnd.ms-excel": [".xls"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
}

def validate_upload(filename: str, file_bytes: bytes):
    """
    Validate file size, extension, and magic bytes (Task 2)
    """
    # 1. Check size
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")

    # 2. Check extension
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        raise HTTPException(status_code=400, detail="File has no extension")

    # 3. Check magic bytes (actual content)
    try:
        # Detected mime using libmagic
        detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    except Exception as e:
        logger.error(f"Magic bytes detection failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Could not determine file type")

    # 4. Check mime is in whitelist
    if detected_mime not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{detected_mime}' is not allowed"
        )

    # 5. Check extension matches detected mime
    allowed_extensions = ALLOWED_TYPES[detected_mime]
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' does not match detected content type '{detected_mime}'"
        )
    
    return True
