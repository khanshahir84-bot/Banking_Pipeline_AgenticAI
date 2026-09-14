"""Identity-provider verification and scope-based authorization boundary."""
from functools import lru_cache

import jwt
from fastapi import HTTPException, Request

from .config import settings


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    if not settings.jwt_jwks_url:
        raise RuntimeError("JWT_JWKS_URL is required when AUTH_MODE=jwks")
    return jwt.PyJWKClient(settings.jwt_jwks_url)


def authenticated_user(request: Request) -> dict:
    """Verify a bearer token and return only its validated claims.

    ``development`` exists solely for local/demo use. Deployed environments must
    set ``AUTH_MODE=jwks`` plus issuer, audience, and bank identity-provider JWKS.
    """
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    token = header.removeprefix("Bearer ")
    try:
        if settings.auth_mode == "jwks":
            if not settings.jwt_issuer or not settings.jwt_audience:
                raise RuntimeError("JWT_ISSUER and JWT_AUDIENCE are required when AUTH_MODE=jwks")
            signing_key = _jwks_client().get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, signing_key, algorithms=["RS256", "ES256"], issuer=settings.jwt_issuer, audience=settings.jwt_audience)
        elif settings.auth_mode == "development":
            claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        else:
            raise RuntimeError("AUTH_MODE must be 'development' or 'jwks'")
    except (jwt.PyJWTError, RuntimeError) as exc:
        raise HTTPException(401, "Invalid identity-provider token") from exc
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise HTTPException(401, "Identity-provider token has no subject")
    return claims


def require_scope(user: dict, scope: str) -> None:
    """Require exact OAuth scope before a specialist can invoke its MCP tool."""
    scopes = set(str(user.get("scope", "")).split())
    if scope not in scopes:
        raise HTTPException(403, f"Missing required scope: {scope}")
