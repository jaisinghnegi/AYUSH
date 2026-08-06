from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_utils import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency for protected routes: validates the Bearer token
    and returns the authenticated user's email, or raises 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    email = decode_access_token(credentials.credentials)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return email


async def get_optional_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> Optional[str]:
    """Like get_current_user_email, but for endpoints that stay public/
    unauthenticated (e.g. the FHIR search operations) and just want to
    attribute the call to a user *when* one is logged in, for audit
    purposes. Never raises -- returns None for missing/invalid tokens."""
    if credentials is None:
        return None
    return decode_access_token(credentials.credentials)
