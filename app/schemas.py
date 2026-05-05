"""
Pydantic Schemas
Request/response validation models with enhanced fields
"""
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import datetime
from app.validators import validate_username_str, validate_email_str
from typing import List, Optional


# ============================================================================
# User Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    role: Optional[str] = Field(default="user", pattern="^(user|admin|auditor)$")

    @field_validator("username")
    @classmethod
    def sanitize_username(cls, v: str) -> str:
        return validate_username_str(v)

    @field_validator("email")
    @classmethod
    def sanitize_email_field(cls, v: str) -> str:
        return validate_email_str(v)

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if v and len(v.encode('utf-8')) > 72:
            raise ValueError("password_too_long")
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Token Schemas
# ============================================================================

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str
    
    @field_validator("email")
    @classmethod
    def sanitize_email_field(cls, v: str) -> str:
        return validate_email_str(v)

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator("new_password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if v and len(v.encode('utf-8')) > 72:
            raise ValueError("password_too_long")
        return v



class TokenData(BaseModel):
    """Schema for JWT token payload"""
    username: Optional[str] = None
    role: Optional[str] = None
    jti: Optional[str] = None
    exp: Optional[int] = None


# ============================================================================
# File Schemas
# ============================================================================

class FileUpload(BaseModel):
    """Schema for file upload metadata"""
    filename: str


class FileResponse(BaseModel):
    """Schema for file response"""
    id: int
    filename: str
    file_hash: str
    owner_id: int
    upload_time: datetime
    is_deleted: bool
    blockchain_tx_hash: Optional[str] = None
    blockchain_index: Optional[int] = None
    is_anomalous: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Access Log Schemas
# ============================================================================

class AccessLogResponse(BaseModel):
    """Schema for access log response"""
    id: int
    user_id: int
    file_id: Optional[int]
    access_time: datetime
    access_status: str
    ip_address: Optional[str]
    device_info: Optional[str]
    action_type: str
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Error Response Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for consistent error responses"""
    detail: str
    error_code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Schema for validation error responses"""
    detail: str
    errors: list

# ============================================================================
# Sharing Schemas
# ============================================================================

class ShareCreate(BaseModel):
    """Schema for creating a share link (v2)"""
    expires_hours: int = Field(default=24, ge=1, le=8760)
    max_uses: int = Field(default=1, ge=1)

class ShareResponse(BaseModel):
    """Schema for share link response (v2)"""
    share_url: str
    token: str
    expires_at: datetime
    max_uses: int
    
    model_config = ConfigDict(from_attributes=True)

class FilePaginationResponse(BaseModel):
    """Schema for paginated file listing (Tasks 16+17)"""
    items: List[FileResponse]
    total: int
    page: int
    limit: int
    pages: int

