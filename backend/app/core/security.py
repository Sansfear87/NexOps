import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt."""
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def generate_session_token() -> str:
    """Generate high-entropy URL-safe session token (64 bytes / ~86 chars)."""
    return secrets.token_urlsafe(64)


def hash_session_token(token: str) -> str:
    """Hash token for indexed lookup if hashing in DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def generate_api_key(prefix: str = "nxp_live_") -> tuple[str, str, str]:
    """Generate high-entropy project API key.

    Returns:
        (raw_key, key_prefix, key_hash)
    """
    secret_part = secrets.token_hex(24)
    raw_key = f"{prefix}{secret_part}"
    key_prefix = raw_key[:16]
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """Hash raw API key using SHA-256 for lookup."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


