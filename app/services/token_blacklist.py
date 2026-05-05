import redis
import logging
from app.config import settings

logger = logging.getLogger(__name__)
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            _redis_client = None
    return _redis_client

def blacklist_token(jti: str, expires_in_seconds: int):
    r = get_redis()
    if r is None:
        logger.warning("Redis down — token blacklist skipped")
        return
    try:
        r.set(jti, "1", ex=expires_in_seconds)
    except Exception as e:
        logger.warning(f"Blacklist write failed: {e}")

def is_blacklisted(jti: str) -> bool:
    r = get_redis()
    if r is None:
        logger.warning("Redis down — blacklist check skipped, allowing request")
        return False
    try:
        return r.exists(jti) == 1
    except Exception as e:
        logger.warning(f"Blacklist read failed: {e}")
        return False
