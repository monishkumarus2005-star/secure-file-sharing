"""
Database Models
Defines SQLAlchemy ORM models with patent-grade features:
- User: RBAC with role field
- File: Blockchain-ready hash + soft delete
- AccessLog: ML-ready logging with IP, device, action type
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """
    User model with Role-Based Access Control (RBAC)
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # user, admin, auditor
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    files: Mapped[List["File"]] = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    access_logs: Mapped[List["AccessLog"]] = relationship("AccessLog", back_populates="user", cascade="all, delete-orphan")
    share_links: Mapped[List["ShareLink"]] = relationship("ShareLink", back_populates="creator")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class File(Base):
    """
    File model with blockchain-ready hashing and soft delete
    """
    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 hash for blockchain anchoring
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    upload_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Soft delete for audit compliance
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)  # Store blockchain transaction hash
    blockchain_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Store index in blockchain registry
    processing_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="files")
    access_logs: Mapped[List["AccessLog"]] = relationship("AccessLog", back_populates="file", cascade="all, delete-orphan")
    share_links: Mapped[List["ShareLink"]] = relationship("ShareLink", back_populates="file", cascade="all, delete-orphan")
    
    # Index for efficient queries
    __table_args__ = (
        Index('ix_files_owner_not_deleted', 'owner_id', 'is_deleted'),
    )
    
    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', hash='{self.file_hash[:8]}...', deleted={self.is_deleted})>"


class AccessLog(Base):
    """
    Access log model with ML-ready fields for anomaly detection
    Captures IP address, device info, and action type
    """
    __tablename__ = "access_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True) # Nullable for public sharing
    file_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("files.id"), nullable=True)  # Nullable for failed access attempts
    access_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    access_status: Mapped[str] = mapped_column(String(20), nullable=False)  # granted, denied
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    device_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # User-Agent string
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)  # upload, download, delete
    is_anomalous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="access_logs")
    file: Mapped[Optional["File"]] = relationship("File", back_populates="access_logs")
    
    # Composite index for ML queries (user activity over time)
    __table_args__ = (
        Index('ix_access_logs_user_time', 'user_id', 'access_time'),
        Index('ix_access_logs_action_time', 'action_type', 'access_time'),
    )
    
    def __repr__(self):
        return f"<AccessLog(id={self.id}, user_id={self.user_id}, action='{self.action_type}', status='{self.access_status}')>"


class RefreshToken(Base):
    """
    Refresh tokens for JWT authentication
    """
    __tablename__ = "refresh_tokens"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # Hashed
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user: Mapped["User"] = relationship("User")


class PasswordResetToken(Base):
    """
    Password reset tokens
    """
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # Hashed SHA256
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    user: Mapped["User"] = relationship("User")


class ShareLink(Base):
    """
    Model for signed time-limited file sharing links (Task 12 Redesign)
    """
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    file: Mapped["File"] = relationship("File", back_populates="share_links")
    creator: Mapped["User"] = relationship("User", back_populates="share_links")

    def __repr__(self):
        return f"<ShareLink(id={self.id}, token='{self.token[:8]}...', active={self.is_active})>"
