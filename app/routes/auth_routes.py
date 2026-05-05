from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas, auth
from app.services import token_blacklist
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=schemas.Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT access and refresh token
    """
    client_host = request.client.host if request.client else "unknown"
    identifier = f"{client_host}:{form_data.username}"
    
    auth.check_rate_limit(identifier)
    
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        auth.record_failed_attempt(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth.clear_failed_attempts(identifier)
    
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    # Generate Refresh token
    raw_rt, hashed_rt = auth.create_refresh_token()
    
    # Store Refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_entry = models.RefreshToken(
        user_id=user.id,
        token=hashed_rt,
        expires_at=expires_at
    )
    db.add(refresh_token_entry)
    db.commit()
    
    return {
        "access_token": access_token, 
        "refresh_token": raw_rt,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(
    data: schemas.TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Issue a new 15-minute access JWT using a valid refresh token.
    Rotates the refresh token.
    """
    hashed_token = auth.hash_token(data.refresh_token)
    
    rt_record = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == hashed_token
    ).first()
    
    if not rt_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    if rt_record.revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
        
    now = datetime.now(timezone.utc)
    expires_at = rt_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
        
    # Valid token found. Issue new access token.
    user = rt_record.user
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    # Rotate refresh token
    rt_record.revoked = True
    
    new_raw_rt, new_hashed_rt = auth.create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    new_rt_record = models.RefreshToken(
        user_id=user.id,
        token=new_hashed_rt,
        expires_at=expires_at
    )
    db.add(new_rt_record)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_raw_rt,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    data: schemas.LogoutRequest,
    db: Session = Depends(get_db),
    current_token: str = Depends(auth.oauth2_scheme)
):
    """
    Revoke current access token (Redis) and optionally a refresh token (DB).
    """
    # 1. Blacklist the current Access Token
    token_data = auth.decode_access_token(current_token)
    if token_data and token_data.jti and token_data.exp:
        # Calculate remaining TTL
        now = int(datetime.now(timezone.utc).timestamp())
        remaining_ttl = token_data.exp - now
        if remaining_ttl > 0:
            token_blacklist.blacklist_token(token_data.jti, remaining_ttl)
    
    # 2. Optionally revoke the Refresh Token
    if data.refresh_token:
        hashed_token = auth.hash_token(data.refresh_token)
        rt_record = db.query(models.RefreshToken).filter(
            models.RefreshToken.token == hashed_token,
            models.RefreshToken.revoked == False
        ).first()
        
        if rt_record:
            rt_record.revoked = True
            db.commit()
        
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    data: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a password reset token and send via email
    """
    user = db.query(models.User).filter(func.lower(models.User.email) == func.lower(data.email)).first()
    
    # We must return 200 even if the user is unknown to prevent email enumeration.
    if user:
        raw_token, hashed_token = auth.create_refresh_token() # same secure generation strategy
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        reset_token_entry = models.PasswordResetToken(
            user_id=user.id,
            token=hashed_token,
            expires_at=expires_at
        )
        db.add(reset_token_entry)
        db.commit()
        
        auth.send_reset_email_mock(user.email, raw_token)
        
    return {"detail": "If that email is registered, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using valid reset token
    """
    hashed_token = auth.hash_token(data.token)
    
    reset_record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == hashed_token
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid token")
        
    if reset_record.used:
        raise HTTPException(status_code=400, detail="Token has already been used")
        
    now = datetime.now(timezone.utc)
    expires_at = reset_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(status_code=400, detail="Token has expired")
        
    # Update password
    user = reset_record.user
    user.hashed_password = auth.hash_password(data.new_password)
    
    # Mark used
    reset_record.used = True
    db.commit()
    
    return {"detail": "Password has been successfully reset."}
