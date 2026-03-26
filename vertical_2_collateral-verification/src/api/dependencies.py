from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from src.core.security import decode_access_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Reads the Authorization: Bearer <token> header,
    decodes the JWT and returns the payload dict.
    Raises 401 if the token is invalid or expired.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload  # {"sub": username, "role": role, "exp": ...}


def require_role(*roles: str):
    """
    Returns a FastAPI dependency that enforces one of the given roles.
    Usage: Depends(require_role("admin"))
    """
    async def role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}.",
            )
        return current_user

    return role_checker
