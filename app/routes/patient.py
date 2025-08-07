import os, json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Request, Cookie
from fastapi.security import HTTPAuthorizationCredentials
from cryptography.fernet import Fernet
from app.security import require_oidc
from app.db.patient_repo import get_bundle, upsert_resources

router = APIRouter()

_env_key = os.getenv("FERNET_KEY", "").strip()
if _env_key:
    try:
        cipher = Fernet(_env_key.encode())
    except Exception:
        raise RuntimeError("FERNET_KEY invalid: must be 32-byte url-safe base64")
else:
    cipher = Fernet(Fernet.generate_key())
    print("🔑 Using ephemeral Fernet key:", cipher._signing_key)  # dev only

def bearer_or_cookie(req: Request, tok: str = Cookie(None)):
    hdr = req.headers.get("Authorization", "")
    if hdr.startswith("Bearer "):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=hdr[7:])
    if tok:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=tok)
    raise HTTPException(401, "No token")

@router.get("/patients/{pid}/data")
def view(pid: str, creds=Depends(bearer_or_cookie)):
    require_oidc(creds)
    b = get_bundle(pid) or HTTPException(404, "Not found")
    return b

@router.get("/patients/{pid}/export")
def export(pid: str, creds=Depends(bearer_or_cookie)):
    require_oidc(creds)
    b = get_bundle(pid) or HTTPException(404, "Not found")
    return cipher.encrypt(json.dumps(b).encode())

@router.post("/patients/{pid}/import")
async def imp(pid: str, file: UploadFile, creds=Depends(bearer_or_cookie)):
    require_oidc(creds)
    try:
        bundle = json.loads(cipher.decrypt(await file.read()))
    except Exception:
        raise HTTPException(400, "Bad or tampered file")
    upsert_resources(pid, bundle)
    return {"ok": True, "imported": len(bundle.get("entry", []))}
