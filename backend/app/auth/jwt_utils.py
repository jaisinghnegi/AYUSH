from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app import config


def create_access_token(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "iat": now,
        "exp": now + timedelta(minutes=config.JWT_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Returns the subject (email) if the token is valid, else None."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
