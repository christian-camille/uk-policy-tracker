from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.config import Settings, get_settings


class AuthenticatedUser:
    def __init__(
        self,
        subject: str,
        email: str | None,
        claims: dict,
    ) -> None:
        self.subject = subject
        self.email = email
        self.claims = claims


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _decode_supabase_access_token(token: str, settings: Settings) -> dict:
    if not settings.SUPABASE_JWKS_URL or not settings.SUPABASE_JWT_ISSUER:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    try:
        signing_key = _get_jwk_client(settings.SUPABASE_JWKS_URL).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=settings.SUPABASE_JWT_ISSUER,
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    claims = _decode_supabase_access_token(credentials.credentials, settings)
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return AuthenticatedUser(
        subject=subject,
        email=claims.get("email"),
        claims=claims,
    )
