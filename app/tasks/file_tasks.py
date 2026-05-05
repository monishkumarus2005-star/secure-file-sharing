from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import File
from app.encryption import encryption_manager
import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from app.storage_service import get_storage_service

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_file_upload(self, file_id: int):
    db = SessionLocal()
    file_record = None
    try:
        file_record = db.query(File).filter(File.id == file_id).first()
        if not file_record:
            raise ValueError(f"File {file_id} not found in DB")

        # Step 1: Encrypt
        file_record.processing_status = "encrypting"
        db.commit()
        
        # Use existing encrypted_path as storage_path
        storage_path = file_record.encrypted_path
        
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"File not found at {storage_path}")

        with open(storage_path, "rb") as f:
            raw = f.read()
        
        encrypted = encryption_manager.encrypt_file(raw)
        
        with open(storage_path, "wb") as f:
            f.write(encrypted)

        # Step 2: Hash
        file_record.processing_status = "hashing"
        db.commit()
        file_record.file_hash = hashlib.sha256(raw).hexdigest()

        # Step 3: Blockchain anchor
        file_record.processing_status = "anchoring"
        db.commit()
        try:
            from app.blockchain_service import get_blockchain_service
            bc = get_blockchain_service()
            # Initialize bc if needed
            if not bc.is_ready:
                bc.initialize()
            
            if bc.is_enabled and bc.is_ready:
                # Use the existing upload_file_to_blockchain method
                blockchain_result = bc.upload_file_to_blockchain(file_record.file_hash, file_record.filename)
                file_record.blockchain_tx_hash = blockchain_result.tx_hash
                
                # Update index if possible
                try:
                    total_files = bc.get_total_files()
                    blockchain_index = int(total_files) - 1
                    if blockchain_index >= 0:
                        file_record.blockchain_index = blockchain_index
                except Exception as index_err:
                    logger.warning(f"Could not get blockchain index: {index_err}")
        except Exception as e:
            logger.warning(f"Blockchain anchor skipped or failed: {e}")

        # Complete
        file_record.processing_status = "complete"
        db.commit()
        logger.info(f"File {file_id} processed successfully")

    except Exception as exc:
        if file_record:
            file_record.processing_status = "failed"
            db.commit()
        logger.error(f"File {file_id} processing failed: {exc}")
        # Retry for transient errors
        raise self.retry(exc=exc)
    finally:
        db.close()

@celery_app.task(name="app.tasks.backup_database")
def backup_database():
    """
    Automated database backup task (Task 10)
    Saves dump/copy to S3/MinIO backups bucket
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"backup_{timestamp}.sql"
    db_url = os.getenv("DATABASE_URL", "sqlite:///./secure_file_sharing.db")

    try:
        # Step 1: Create backup file
        if "postgresql" in db_url:
            # Assumes pg_dump is available in the environment
            logger.info("Starting PostgreSQL backup...")
            result = subprocess.run(
                ["pg_dump", db_url, "-f", filename],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
        else:
            # Default to SQLite behavior
            logger.info("Starting SQLite backup...")
            db_path = db_url.replace("sqlite:///", "")
            if not os.path.exists(db_path):
                # Fallback for current project path
                db_path = "./secure_file_sharing.db"
                
            import shutil
            shutil.copy(db_path, filename)

        # Step 2: Upload to S3
        with open(filename, "rb") as f:
            backup_data = f.read()

        storage = get_storage_service()
        # Upload to the predefined secure-files bucket under the 'backups' prefix
        s3_key = f"backups/{filename}"
        success = storage.save_file(
            s3_key,
            backup_data
        )

        if success:
            logger.info(f"Backup completed and uploaded: {s3_key}")
            
            # Step 4: Prune old backups (older than 7 days)
            try:
                if storage.s3_enabled:
                    s3_client = storage._get_client()
                    retention_date = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=7)
                    bucket = __import__('app.config', fromlist=['settings']).settings.S3_BUCKET_NAME
                    response = s3_client.list_objects_v2(Bucket=bucket, Prefix="backups/")
                    if "Contents" in response:
                        for obj in response["Contents"]:
                            if obj["LastModified"] < retention_date:
                                s3_client.delete_object(Bucket=bucket, Key=obj["Key"])
                                logger.info(f"Pruned old backup: {obj['Key']}")
            except Exception as prune_exc:
                logger.error(f"Failed to prune old backups: {prune_exc}")
        else:
            logger.error("Backup file created but S3 upload failed")

        # Step 3: Cleanup local temp file
        if os.path.exists(filename):
            os.remove(filename)

        return {"status": "success" if success else "partial_failure", "filename": filename}

    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        # Cleanup if error happened after file creation
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)
        return {"status": "failed", "error": str(e)}
