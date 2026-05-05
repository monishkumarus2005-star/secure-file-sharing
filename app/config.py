"""
Centralized Configuration Module
Loads environment variables and provides typed configuration settings
"""
import re
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./secure_file_sharing.db",
        description="Database connection URL (SQLite for dev, PostgreSQL for production)"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="Secret key for JWT token encoding/decoding"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used for JWT encoding"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="JWT token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        description="Refresh token expiration time in days"
    )
    
    # Encryption Configuration
    ENCRYPTION_KEY_PATH: str = Field(
        default="./encryption.key",
        description="Path to the encryption key file"
    )
    
    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Application Configuration
    APP_NAME: str = Field(
        default="Secure Cloud File Sharing System",
        description="Application name"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag"
    )
    DOMAIN_NAME: str = Field(
        default="localhost",
        description="Domain name for the application"
    )
    
    # File Upload Configuration
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Directory for storing encrypted files"
    )
    
    # S3 / MinIO Configuration (Task 10)
    S3_ENABLED: bool = Field(default=False)
    S3_ENDPOINT_URL: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_NAME: str = Field(default="secure-files")
    S3_REGION: str = Field(default="us-east-1")
    
    # File Security Configuration
    MAX_UPLOAD_SIZE: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="Maximum allowed file size in bytes"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["pdf", "docx", "xlsx", "jpg", "jpeg", "png", "gif", "txt", "csv", "zip"],
        description="Whitelist of allowed file extensions"
    )
    ALLOWED_MIME_TYPES: List[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "image/jpeg",
            "image/png",
            "image/gif",
            "text/plain",
            "text/csv",
            "application/zip"
        ],
        description="Whitelist of allowed MIME types (verified by magic bytes)"
    )

    
    # Rate Limiting Configuration
    RATE_LIMIT_LOGIN: str = Field(
        default="5/minute",
        description="Rate limit for login attempts"
    )

    # Blockchain Configuration
    BLOCKCHAIN_ENABLED: bool = Field(
        default=False,
        description="Enable/disable blockchain integration"
    )
    WEB3_PROVIDER_URL: str = Field(
        default="http://127.0.0.1:8545",
        description="Web3 HTTP provider URL for blockchain node"
    )
    BLOCKCHAIN_NODE_URL: Optional[str] = Field(
        default=None,
        description="Legacy field - use WEB3_PROVIDER_URL instead"
    )
    PRIVATE_KEY: Optional[str] = Field(
        default=None,
        description="Private key for blockchain transactions (64 hex chars, optional 0x prefix)"
    )
    CONTRACT_ADDRESS: Optional[str] = Field(
        default=None,
        description="Ethereum contract address (0x + 40 hex chars)"
    )
    
    @field_validator("PRIVATE_KEY")
    @classmethod
    def validate_private_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Ethereum private key format"""
        if v is None or v.strip() == "":
            return None
        
        key = v.strip()
        if key.startswith("0x") or key.startswith("0X"):
            key = key[2:]
        
        if len(key) != 64:
            raise ValueError(f"Private key must be 64 hex characters (got {len(key)})")
        
        if not re.match(r"^[0-9a-fA-F]+$", key):
            raise ValueError("Private key contains non-hexadecimal characters")
        
        return v.strip()
    
    @field_validator("CONTRACT_ADDRESS")
    @classmethod
    def validate_contract_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate Ethereum contract address format"""
        if v is None or v.strip() == "":
            return None
        
        addr = v.strip()
        
        if len(addr) != 42:
            raise ValueError(f"Contract address must be 42 characters (0x + 40 hex, got {len(addr)})")
        
        if not addr.startswith("0x"):
            raise ValueError("Contract address must start with '0x'")
        
        if not re.match(r"^0x[0-9a-fA-F]{40}$", addr):
            raise ValueError("Contract address must be hex format (0x + 40 hex characters)")
        
        return addr
    
    @model_validator(mode='after')
    def validate_blockchain_config(self):
        if self.BLOCKCHAIN_NODE_URL and not self.WEB3_PROVIDER_URL:
            self.WEB3_PROVIDER_URL = self.BLOCKCHAIN_NODE_URL
        
        if self.BLOCKCHAIN_ENABLED:
            if not self.PRIVATE_KEY:
                raise ValueError("PRIVATE_KEY is required when BLOCKCHAIN_ENABLED=true")
            if not self.CONTRACT_ADDRESS:
                raise ValueError("CONTRACT_ADDRESS is required when BLOCKCHAIN_ENABLED=true")
            
            # Validate private key format
            if not self.validate_private_key(self.PRIVATE_KEY):
                raise ValueError("Private key must be 64 hex characters")
            
            # Validate contract address format
            if not self.validate_contract_address(self.CONTRACT_ADDRESS):
                raise ValueError("Contract address must be valid Ethereum address")
        
        return self
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def blockchain_configured(self) -> bool:
        """Check if blockchain is fully configured and can be enabled"""
        return (
            self.BLOCKCHAIN_ENABLED 
            and self.PRIVATE_KEY is not None 
            and self.CONTRACT_ADDRESS is not None
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
