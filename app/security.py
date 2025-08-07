import os, httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.jose import jwt, JsonWebKey

ISSUER     = os.getenv("OIDC_ISSUER")
CLIENT_ID  = os.getenv("OIDC_CLIENT_ID")
JWKS_URI   = f"{ISSUER}/protocol/openid-connect/certs"

bearer = HTTPBearer()
_jwks  = None

def _jwks():
    global _jwks
    if _jwks is None:
        _jwks = JsonWebKey.import_key_set(httpx.get(JWKS_URI).json())
    return _jwks

def require_oidc(creds: HTTPAuthorizationCredentials = Security(bearer)):
    try:
        claims = jwt.decode(creds.credentials, _jwks())
        claims.validate()
    except Exception:
        raise HTTPException(401, "Invalid token")

    if claims.get("iss") != ISSUER:
        raise HTTPException(401, "Bad issuer")
    aud = claims.get("aud")
    if (isinstance(aud, list) and CLIENT_ID not in aud) or aud == CLIENT_ID:
        pass  # ok
    else:
        raise HTTPException(401, "Bad audience")

    if "patient/*.read" not in claims.get("scope", "").split():
        raise HTTPException(403, "Missing scope")
    return claims
