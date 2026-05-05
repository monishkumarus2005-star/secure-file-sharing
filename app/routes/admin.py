"""
Admin Routes
Handles admin-only operations like system integrity scanning
"""
import os
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from datetime import datetime

from app import models, auth
from app.database import get_db
from app.blockchain_service import get_blockchain_service

# Initialize router
router = APIRouter(prefix="/admin", tags=["admin"])

# Set up logging
logger = logging.getLogger(__name__)


@router.get("/scan-integrity")
async def scan_system_integrity(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only system integrity scanner
    
    Scans all files in the system and verifies their integrity against blockchain records.
    
    Returns:
        - Total files scanned
        - Valid files count
        - Lists of problematic files with reasons
    
    Requires admin role (role == "admin")
    """
    # Verify admin role
    if current_user.role != "admin":
        logger.warning(f"Non-admin user {current_user.username} attempted integrity scan")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.info(f"Starting system integrity scan by admin: {current_user.username}")
    
    # Initialize results
    scan_results = {
        "total_files_scanned": 0,
        "valid_files": 0,
        "tampered_files": [],
        "missing_files": [],
        "not_anchored": []
    }
    
    try:
        # Fetch all non-deleted files
        files = db.query(models.File).filter(models.File.is_deleted.is_(False)).all()
        scan_results["total_files_scanned"] = len(files)
        
        logger.info(f"Found {len(files)} files to scan")
        
        for file in files:
            try:
                # Check if file is anchored on blockchain
                if file.blockchain_index is None:
                    scan_results["not_anchored"].append({
                        "file_id": file.id,
                        "reason": f"File '{file.filename}' is not registered on blockchain"
                    })
                    logger.warning(f"File {file.id} not anchored on blockchain")
                    continue
                
                # Check if file exists on disk
                if not os.path.exists(file.encrypted_path):
                    scan_results["missing_files"].append({
                        "file_id": file.id,
                        "reason": f"File '{file.filename}' not found at path: {file.encrypted_path}"
                    })
                    logger.error(f"File {file.id} missing from disk at {file.encrypted_path}")
                    continue
                
                # Calculate file hash
                try:
                    with open(file.encrypted_path, "rb") as f:
                        file_content = f.read()
                    calculated_hash = hashlib.sha256(file_content).hexdigest()
                except Exception as e:
                    scan_results["missing_files"].append({
                        "file_id": file.id,
                        "reason": f"Failed to read file '{file.filename}': {str(e)}"
                    })
                    logger.error(f"Failed to read file {file.id}: {str(e)}")
                    continue
                
                # Fetch blockchain hash
                bc_service = get_blockchain_service()
                if not bc_service.is_ready:
                    scan_results["tampered_files"].append({
                        "file_id": file.id,
                        "reason": "Blockchain service not available"
                    })
                    logger.warning(f"Blockchain not available for file {file.id}")
                    continue
                
                try:
                    blockchain_data = bc_service.get_file_from_blockchain(file.blockchain_index)
                    blockchain_hash = blockchain_data["file_hash"]
                except Exception as e:
                    # Log blockchain error but continue scanning
                    scan_results["tampered_files"].append({
                        "file_id": file.id,
                        "reason": f"Failed to verify against blockchain: {str(e)}"
                    })
                    logger.error(f"Blockchain verification failed for file {file.id}: {str(e)}")
                    continue
                
                # Compare hashes
                if calculated_hash == blockchain_hash:
                    scan_results["valid_files"] += 1
                    logger.debug(f"File {file.id} verified: VALID")
                else:
                    scan_results["tampered_files"].append({
                        "file_id": file.id,
                        "reason": f"File '{file.filename}' has been modified (hash mismatch)"
                    })
                    logger.warning(f"File {file.id} verification: TAMPERED - hash mismatch")
                
            except Exception as e:
                # Log individual file errors but continue scanning
                logger.error(f"Unexpected error scanning file {file.id}: {str(e)}")
                scan_results["tampered_files"].append({
                    "file_id": file.id,
                    "reason": f"Scanning error: {str(e)}"
                })
                continue
        
        # Log final summary
        logger.info(f"Integrity scan completed. Total: {scan_results['total_files_scanned']}, "
                   f"Valid: {scan_results['valid_files']}, "
                   f"Tampered: {len(scan_results['tampered_files'])}, "
                   f"Missing: {len(scan_results['missing_files'])}, "
                   f"Not anchored: {len(scan_results['not_anchored'])}")
        
        return scan_results
        
    except Exception as e:
        logger.error(f"Critical error during integrity scan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integrity scan failed"
        )


@router.get("/anomaly-report")
async def get_anomaly_report(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only anomaly detection report
    
    Returns statistics about anomalous access patterns detected by ML.
    
    Requires admin role (role == "admin")
    """
    # Verify admin role
    if current_user.role != "admin":
        logger.warning(f"Non-admin user {current_user.username} attempted to access anomaly report")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get total logs count
        total_logs = db.query(models.AccessLog).count()
        
        # Get anomalous logs with details
        anomalous_logs = db.query(models.AccessLog).filter(
            models.AccessLog.is_anomalous.is_(True)
        ).order_by(models.AccessLog.access_time.desc()).limit(100).all()
        
        # Format anomalous logs for response
        anomalies = []
        for log in anomalous_logs:
            access_time: datetime = log.access_time  # type: ignore
            anomalies.append({
                "user_id": log.user_id,
                "file_id": log.file_id,
                "timestamp": access_time.isoformat(),
                "action_type": log.action_type,
                "access_status": log.access_status,
                "ip_address": log.ip_address,
                "device_info": log.device_info
            })
        
        report = {
            "total_logs": total_logs,
            "anomalies": anomalies
        }
        
        logger.info(f"Anomaly report generated by admin {current_user.username}: {len(anomalies)} anomalies found")
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate anomaly report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anomaly report generation failed"
        )
@router.post("/backup", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_backup(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin-only manual database backup trigger (Task 10)
    
    Triggers the background Celery task to dump the database and upload to MinIO.
    
    Requires admin role (role == "admin")
    """
    # Verify admin role
    if current_user.role != "admin":
        logger.warning(f"Non-admin user {current_user.username} attempted manual backup trigger")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    from app.tasks.file_tasks import backup_database
    
    try:
        task = backup_database.delay()
        logger.info(f"Manual backup triggered by admin {current_user.username}, Task ID: {task.id}")
        return {
            "status": "backup started", 
            "task_id": task.id,
            "message": "The backup process is running in the background."
        }
    except Exception as e:
        logger.error(f"Failed to trigger backup task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate backup process"
        )
