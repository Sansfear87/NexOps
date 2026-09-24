import secrets
import hashlib
import bcrypt


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
