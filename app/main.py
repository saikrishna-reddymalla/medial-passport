import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from authlib.integrations.starlette_client import OAuth

app = FastAPI(title="Digital Medical Passport – SMART MVP")

# ── Session for PKCE state ─────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change_this_in_prod")
)

# ── OIDC / Keycloak client ─────────────────────────────────────
oauth = OAuth()
oauth.register(
    name="kc",
    client_id=os.getenv("OIDC_CLIENT_ID"),
    client_secret=os.getenv("OIDC_CLIENT_SECRET", None),  # blank for public client
    server_metadata_url=f"{os.getenv('OIDC_ISSUER')}/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile patient/*.read"}
)

@app.get("/login")
async def login(req: Request):
    return await oauth.kc.authorize_redirect(
        req, req.url_for("auth_callback")
    )

@app.get("/auth/callback")
async def auth_callback(req: Request):
    token = await oauth.kc.authorize_access_token(req)
    resp = RedirectResponse("/")
    resp.set_cookie("access_token", token["access_token"], httponly=True)
    return resp

# ── API routes (SMART-protected) ───────────────────────────────
from app.routes.patient import router as patient_router
app.include_router(patient_router, prefix="/api")

# ── Static UI LAST so it doesn’t shadow /login ─────────────────
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
