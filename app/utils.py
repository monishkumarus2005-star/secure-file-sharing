import re
import magic
import logging
from typing import Optional, Tuple
from werkzeug.utils import secure_filename
from app.config import settings

logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and remove non-ASCII characters.
    Uses werkzeug.utils.secure_filename as a base.
    """
    if not filename:
        return f"unnamed_file_{id(filename)}"
    
    # 1. Use secure_filename to strip path separators and control characters
    safe_name = secure_filename(filename)
    
    # 2. If the filename became empty (e.g. it was only ../../ or non-ascii), provide a fallback
    if not safe_name:
        # Fallback to a predictable name if everything was stripped
        safe_name = f"sanitized_file_{id(filename)}"
        
    return safe_name

def validate_file_security(content: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validates file size, extension, and MIME type using magic bytes.
    
    Returns:
        (bool, str): (Is valid, Error message)
    """
    # 1. Size check
    if len(content) > settings.MAX_UPLOAD_SIZE:
        return False, f"File too large. Max allowed: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
    
    # 2. Extension check
    ext = filename.split('.')[-1].lower() if '.' in filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        return False, f"File extension '.{ext}' is not allowed"
    
    # 3. MIME type check (Magic Bytes)
    try:
        mime_detector = magic.Magic(mime=True)
        detected_mime = mime_detector.from_buffer(content)
        
        if detected_mime not in settings.ALLOWED_MIME_TYPES:
            logger.warning(f"Security: Mismatched/Disallowed MIME type detected: {detected_mime} for file {filename}")
            return False, f"File type '{detected_mime}' is not allowed"
            
        return True, ""
    except Exception as e:
        logger.error(f"Error during MIME type detection: {str(e)}")
        return False, "Failed to verify file type integrity"

def strip_html(text: str) -> str:
    """
    Strip HTML tags and script/style content from a string to prevent XSS.
    Used in Pydantic validators.
    """
    if not text:
        return text
        
    # Remove script and style tags and their content
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove control characters (including null bytes)
    text = "".join(ch for ch in text if ch.isprintable())
    
    return text.strip()
