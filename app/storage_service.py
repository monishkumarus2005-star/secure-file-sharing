import boto3
from botocore.client import Config
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.s3_enabled = settings.S3_ENABLED
        if self.s3_enabled:
            self.client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                config=Config(signature_version='s3v4')
            )
        else:
            self.client = None

    def _get_client(self):
        """Internal method for direct client access as requested by spec"""
        return self.client

    def save_file(self, file_path: str, data: bytes, bucket: str = None):
        """Upload a file to S3"""
        if not self.s3_enabled:
            logger.warning("S3 is disabled, skipping upload")
            return False
        
        target_bucket = bucket or settings.S3_BUCKET_NAME
        try:
            self.client.put_object(
                Bucket=target_bucket,
                Key=file_path,
                Body=data
            )
            logger.info(f"Successfully uploaded to {target_bucket}/{file_path}")
            return True
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}")
            return False

_storage_service = None

def get_storage_service():
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
