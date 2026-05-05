import re
from typing import Optional
from email_validator import validate_email, EmailNotValidError

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and arbitrary file creation.
    - strip ../, null bytes, path separators
    - allow [a-zA-Z0-9._-] only
    - max 255 chars
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
        
    if '\x00' in filename:
        raise ValueError("Filename cannot contain null bytes")
        
    if '..' in filename or '/' in filename or '\\\\' in filename:
        raise ValueError("Path traversal detected in filename")
    
    # Allow only safe characters
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        raise ValueError("Filename contains invalid characters")
        
    # Prevent empty filename after stripping
    if len(filename) > 255:
        raise ValueError("Filename too long")
        
    return filename

def validate_username_str(username: str) -> str:
    """
    Validate username: alphanumeric + underscore, 3-30 chars
    """
    if not username:
        raise ValueError("Username cannot be empty")
    
    if len(username) < 3 or len(username) > 30:
        raise ValueError("Username must be between 3 and 30 characters")
        
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValueError("Username must be alphanumeric and underscores only")
        
    return username

def validate_email_str(email: str) -> str:
    """
    Validate email using email-validator library
    """
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError as e:
        raise ValueError(str(e))
