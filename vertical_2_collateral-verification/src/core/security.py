import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "fallback_secret")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(username: str, role: str) -> str:
    """Generate a signed JWT containing sub and role claims."""
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=EXPIRE_MIN)
    payload = {
        "sub":  username,
        "role": role,
        "exp":  expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT.
    Returns the full payload dict on success.
    Raises jwt.PyJWTError on failure.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])