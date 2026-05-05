"""
File Routes
Handles file upload, download, and deletion with encryption and access logging
"""
import os
import uuid
import hashlib
import logging
from datetime import datetime, timedelta, timezone, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
import secrets
import math


from app import models, schemas, auth
from app.database import get_db
from app.encryption import encryption_manager
from app.config import settings
from app.blockchain_service import get_blockchain_service
from app.validators import sanitize_filename
from app.tasks.file_tasks import process_file_upload
from app.services.file_validator import validate_upload

# Initialize router
router = APIRouter(prefix="/files", tags=["files"])

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Set up logging
logger = logging.getLogger(__name__)

# File Validation Constants (Task 2)
ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls",
    "txt", "csv", "jpg", "jpeg", "png",
    "gif", "webp", "zip", "tar", "gz"
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/zip", "application/x-tar", "application/gzip", "application/x-gzip"
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG": "png",
    b"PK\x03\x04": "zip/docx/xlsx",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file for background processing
    
    - Saves raw file to disk
    - Creates database record with status 'pending'
    - Triggers background encryption and anchoring
    
    Returns 202 Accepted with file_id
    """
    try:
        user_id = current_user.id
        
        # Validation Check 1: Extension (Task 2)
        if "." not in file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File has no extension"
            )
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type .{ext} not allowed"
            )
            
        # Validation Check 2: MIME Type (Task 2)
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type {file.content_type} not allowed"
            )

        # Read content for validation and processing (Task 2)
        file_content = await file.read()
        
        # Comprehensive Validation (Size, Extension, Magic Bytes)
        validate_upload(file.filename, file_content)

        # Sanitize filename
        try:
            safe_filename = sanitize_filename(file.filename)
        except ValueError as val_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
        
        # Save raw file immediately
        unique_filename = f"{uuid.uuid4()}_{safe_filename}"
        storage_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        with open(storage_path, "wb") as f:
            f.write(file_content)
        
        # Create file record (hash will be populated by worker)
        db_file = models.File(
            filename=safe_filename,
            encrypted_path=storage_path,
            file_hash="pending",  # Placeholder until worker computes it
            owner_id=user_id,
            processing_status="pending"
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        file_id = db_file.id
        
        # Log upload attempt
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", None)
        from app.file_service import file_service
        file_service.log_access(
            db=db,
            user_id=user_id,
            file_id=file_id,
            action_type="upload",
            access_status="success",
            ip_address=ip_address,
            device_info=device_info,
            is_anomalous=False
        )
        
        # Trigger background processing
        process_file_upload.delay(file_id)
        
        return {
            "id": file_id,
            "filename": safe_filename,
            "status": "pending",
            "message": "File upload accepted and processing started"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )


@router.get("/{file_id}/status")
async def get_file_status(
    file_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check the processing status of an uploaded file
    """
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.owner_id == current_user.id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "status": file.processing_status,
        "blockchain_tx_hash": file.blockchain_tx_hash
    }


@router.get("/download/{file_id}")
async def download_file(
    file_id: int,
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    verify_hash: bool = True
):
    """
    Download and decrypt a file with hash verification
    """
    from app.file_service import file_service
    
    # Get file from database
    db_file = db.query(models.File).filter(models.File.id == file_id).first()
    
    # If file not found OR is_deleted=True -> raise 404 for ALL users including admin
    if not db_file or (db_file.is_deleted if db_file.is_deleted is not None else False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # If not owner AND not admin -> call create_access_log with status="denied", then raise 403
    has_access, is_anomalous = file_service.verify_file_access(db_file, current_user)
    if not has_access:
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", None)
        file_service.log_access(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            action_type="download",
            access_status="denied",
            ip_address=ip_address,
            device_info=device_info,
            is_anomalous=is_anomalous
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You don't have permission to access this file."
        )
    
    try:
        # Process download with hash verification
        decrypted_content, filename = file_service.process_download(db_file, verify_hash=verify_hash)
        
        # On success -> call create_access_log with status="success"
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", None)
        file_service.log_access(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            action_type="download",
            access_status="success",
            ip_address=ip_address,
            device_info=device_info,
            is_anomalous=False
        )
        
        # Return file as streaming response
        return StreamingResponse(
            BytesIO(decrypted_content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File download failed"
        )


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: int,
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a file (maintains audit trail)
    """
    from app.file_service import file_service

    # Query the file FIRST
    db_file = db.query(models.File).filter(models.File.id == file_id).first()
    
    # If not found OR already is_deleted=True → raise 404 immediately
    if not db_file or db_file.is_deleted is not None and db_file.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check ownership: if file.owner_id != current_user.id AND role != "admin" → raise 403
    if db_file.owner_id != current_user.id and current_user.role != "admin":
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", None)
        file_service.log_access(
            db=db,
            user_id=current_user.id,
            file_id=file_id,
            action_type="delete",
            access_status="denied",
            ip_address=ip_address,
            device_info=device_info,
            is_anomalous=False
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You don't have permission to delete this file."
        )
    
    # Only THEN set is_deleted = True and commit
    db_file.is_deleted = True
    db.commit()
    
    # Call create_access_log() with action_type="delete", access_status="success"
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent", None)
    file_service.log_access(
        db=db,
        user_id=current_user.id,
        file_id=file_id,
        action_type="delete",
        access_status="success",
        ip_address=ip_address,
        device_info=device_info,
        is_anomalous=False
    )
    
    return {"detail": "File deleted successfully", "file_id": file_id}


@router.get("/", response_model=schemas.FilePaginationResponse)
async def list_user_files(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    show_deleted: bool = False,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    List files with pagination and search filters (Tasks 16+17)
    
    - **page**: Page number (default: 1)
    - **limit**: Files per page (default: 20, max: 100)
    - **search**: Filter by filename (case-insensitive)
    - **from_date**: Uploaded on or after YYYY-MM-DD
    - **to_date**: Uploaded on or before YYYY-MM-DD
    - **show_deleted**: Include soft-deleted files (Admin only)
    """
    # Enforce limit constraints
    limit = min(max(1, limit), 100)
    page = max(1, page)
    
    # Base query
    query = db.query(models.File).filter(models.File.owner_id == current_user.id)
    
    # Apply search filter
    if search:
        query = query.filter(models.File.filename.ilike(f"%{search}%"))
    
    # Apply date filters
    if from_date:
        query = query.filter(models.File.upload_time >= from_date)
    if to_date:
        # Adjustment to include the whole 'to_date' day
        query = query.filter(models.File.upload_time < (to_date + timedelta(days=1)))
        
    # Apply soft-delete filter
    if not (show_deleted and current_user.role == "admin"):
        query = query.filter(models.File.is_deleted.is_(False))
    
    # Count total for pagination metadata
    total = query.count()
    pages = math.ceil(total / limit) if total > 0 else 1
    
    # Apply pagination
    files = query.order_by(models.File.upload_time.desc())\
                 .offset((page - 1) * limit)\
                 .limit(limit)\
                 .all()
                 
    return {
        "items": files,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


@router.get("/{file_id}/verify")
async def verify_file_integrity(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Verify file integrity against storage and blockchain record
    """
    from app.file_service import file_service
    
    # 1. Query file by id where is_deleted=False -> 404 if missing
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.is_deleted.is_(False)
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # 2. Open file.encrypted_path and compute SHA-256 hash
    if not os.path.exists(file.encrypted_path):
        # 3. If FileNotFoundError -> raise 500 "File missing from storage"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File missing from storage"
        )
        
    try:
        with open(file.encrypted_path, "rb") as f:
            encrypted_content = f.read()
        
        # Decrypt first, then hash (to match upload logic)
        decrypted_content = encryption_manager.decrypt_file(encrypted_content)
        current_hash = hashlib.sha256(decrypted_content).hexdigest()
        
        # 4. Compare current_hash with file.file_hash
        hash_matches = (current_hash == file.file_hash)
        
        # 5. If BLOCKCHAIN_ENABLED:
        blockchain_match = None
        bc_service = get_blockchain_service()
        if bc_service.is_enabled:
            try:
                if file.blockchain_index is not None:
                    blockchain_data = bc_service.get_file_from_blockchain(file.blockchain_index)
                    blockchain_hash = blockchain_data["file_hash"]
                    blockchain_match = (blockchain_hash == file.file_hash)
            except Exception as e:
                logger.error(f"Blockchain verification failed for file {file_id}: {str(e)}")
                blockchain_match = None
        
        # Return result
        return {
            "file_id": file_id,
            "filename": file.filename,
            "stored_hash": file.file_hash,
            "current_hash": current_hash,
            "integrity_ok": hash_matches,
            "blockchain_verified": blockchain_match,
            "verified_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Integrity check failed for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity check failed: {str(e)}"
        )
# ============================================================================
# Task 12: File Sharing (Redesign)
# ============================================================================

@router.post("/{file_id}/share", response_model=schemas.ShareResponse)
async def share_file(
    file_id: int,
    share_data: schemas.ShareCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a signed time-limited and use-limited sharing link
    """
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.owner_id == current_user.id,
        models.File.is_deleted.is_(False)
    ).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Generate token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=share_data.expires_hours)

    # Create link record
    new_link = models.ShareLink(
        file_id=file_id,
        token=token,
        created_by=current_user.id,
        expires_at=expires_at,
        max_uses=share_data.max_uses,
        use_count=0,
        is_active=True
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    # Construct URL (assuming base URL context or settings)
    # For this exercise, we'll use a hardcoded base or detect it
    base_url = str(settings.API_URL).rstrip("/") if hasattr(settings, "API_URL") else "http://127.0.0.1:8000"
    share_url = f"{base_url}/files/share/{token}"

    return {
        "share_url": share_url,
        "token": token,
        "expires_at": expires_at,
        "max_uses": share_data.max_uses
    }


@router.get("/share/{token}")
async def download_shared_file(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public access to shared files via signed token (Task 12 consumption)
    """
    from app.file_service import file_service

    # Find link
    link = db.query(models.ShareLink).filter(models.ShareLink.token == token).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid share link"
        )

    if not link.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link is no longer active"
        )

    # Check expiry (safe comparison for SQLite)
    now = datetime.now(timezone.utc)
    expires_at = link.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        link.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )

    # Check use count
    if link.use_count >= link.max_uses:
        link.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Maximum download limit reached"
        )

    # Get file content
    file = db.query(models.File).filter(models.File.id == link.file_id).first()
    if not file or file.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file has been removed"
        )

    try:
        # Decrypt file
        decrypted_content, filename = file_service.process_download(file, verify_hash=True)

        # Update link usage
        link.use_count += 1
        if link.use_count >= link.max_uses:
            link.is_active = False
        db.commit()

        # Log access (Anonymous)
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", None)
        file_service.log_access(
            db=db,
            user_id=None,  # Public access
            file_id=file.id,
            action_type="share_download",
            access_status="granted",
            ip_address=ip_address,
            device_info=device_info,
            is_anomalous=False
        )

        return StreamingResponse(
            BytesIO(decrypted_content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"Shared download failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Download failed"
        )


@router.get("/{file_id}/shares", response_model=List[schemas.ShareResponse])
async def list_file_shares(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    List all active share links for a specific file
    Only the owner can list shares
    """
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.owner_id == current_user.id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
        
    shares = db.query(models.ShareLink).filter(
        models.ShareLink.file_id == file_id,
        models.ShareLink.is_active == True
    ).all()
    
    base_url = str(settings.API_URL).rstrip("/") if hasattr(settings, "API_URL") else "http://127.0.0.1:8000"
    
    # Map to schema
    return [
        {
            "share_url": f"{base_url}/files/share/{s.token}",
            "token": s.token,
            "expires_at": s.expires_at,
            "max_uses": s.max_uses
        } for s in shares
    ]


@router.delete("/{file_id}/share/{token}", status_code=status.HTTP_200_OK)
async def revoke_share_link(
    file_id: int,
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Revoke a specific share link
    Only the owner can revoke
    """
    file = db.query(models.File).filter(
        models.File.id == file_id,
        models.File.owner_id == current_user.id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
        
    share = db.query(models.ShareLink).filter(
        models.ShareLink.file_id == file_id,
        models.ShareLink.token == token
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
        
    share.is_active = False
    db.commit()
    
    return {"message": "Share link revoked successfully"}
