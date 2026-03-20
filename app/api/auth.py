"""
MetaPM PL Authentication — Google OAuth 2.0
Provides session management for PL-authenticated UAT pages (MP-UAT-SERVER-001).
"""
import hashlib
import hmac
import logging
import time
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Session cookie configuration
SESSION_COOKIE = "pl_session"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days


# ── Session helpers ─────────────────────────────────────────────────────────

def _sign(payload: str) -> str:
    """HMAC-sign a payload string."""
    return hmac.new(
        settings.SESSION_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def create_session_token(email: str) -> str:
    """Create a signed session token: email|timestamp|signature"""
    ts = str(int(time.time()))
    payload = f"{email}|{ts}"
    sig = _sign(payload)
    return f"{payload}|{sig}"


def verify_session_token(token: str) -> Optional[str]:
    """Verify a session token. Returns email if valid, None if invalid/expired."""
    try:
        parts = token.split("|")
        if len(parts) != 3:
            return None
        email, ts_str, sig = parts
        payload = f"{email}|{ts_str}"
        expected_sig = _sign(payload)
        if not hmac.compare_digest(sig, expected_sig):
            return None
        ts = int(ts_str)
        if time.time() - ts > SESSION_MAX_AGE:
            return None
        return email
    except Exception:
        return None


def get_session_email(request: Request) -> Optional[str]:
    """Extract and verify the PL session from cookie. Returns email or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return verify_session_token(token)


def is_pl_authenticated(request: Request) -> bool:
    """Check if the request has a valid PL session for cprator@cbsware.com."""
    email = get_session_email(request)
    return email == settings.PL_EMAIL


# ── OAuth endpoints ─────────────────────────────────────────────────────────

@router.get("/app/login")
async def oauth_login(request: Request, next: str = "/"):
    """Redirect to Google OAuth. If OAuth not configured, show error page."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return HTMLResponse(_render_oauth_not_configured(), status_code=503)

    try:
        from google_auth_oauthlib.flow import Flow
        redirect_uri = str(request.base_url).rstrip("/") + "/app/oauth-callback"
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
        )
        flow.redirect_uri = redirect_uri
        auth_url, state = flow.authorization_url(
            access_type="online",
            include_granted_scopes="true",
            state=next,
            prompt="select_account",
        )
        return RedirectResponse(auth_url)
    except Exception as e:
        logger.error(f"OAuth login error: {e}")
        return HTMLResponse(f"<h1>Login error</h1><p>{e}</p>", status_code=500)


@router.get("/app/oauth-callback")
async def oauth_callback(request: Request):
    """Handle Google OAuth callback. Verify email = PL_EMAIL, set session cookie."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return HTMLResponse(_render_oauth_not_configured(), status_code=503)

    code = request.query_params.get("code")
    state = request.query_params.get("state", "/")
    if not code:
        return HTMLResponse("<h1>OAuth error: no code</h1>", status_code=400)

    try:
        from google_auth_oauthlib.flow import Flow
        import httpx as _httpx
        redirect_uri = str(request.base_url).rstrip("/") + "/app/oauth-callback"
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
            state=state,
        )
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Get user email from Google
        resp = _httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"}
        )
        user_info = resp.json()
        email = user_info.get("email", "")

        if email != settings.PL_EMAIL:
            return HTMLResponse(_render_unauthorized(email), status_code=403)

        # Create session and redirect
        token = create_session_token(email)
        next_url = state if state.startswith("/") else "/"
        response = RedirectResponse(next_url, status_code=302)
        response.set_cookie(
            SESSION_COOKIE, token,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=True,
        )
        logger.info(f"PL authenticated: {email}")
        return response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return HTMLResponse(f"<h1>Authentication error</h1><p>{e}</p>", status_code=500)


@router.get("/app/logout")
async def logout():
    """Clear PL session cookie."""
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ── HTML templates ───────────────────────────────────────────────────────────

def render_login_required_page(uat_url: str, spec_id: str) -> str:
    """Render the 'PL authentication required' page for unauthenticated UAT access."""
    login_url = f"/app/login?next={uat_url}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UAT — Authentication Required</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f1117; color: #c9d1d9; min-height: 100vh;
      display: flex; align-items: center; justify-content: center; margin: 0; }}
    .card {{ background: #161b22; border: 1px solid #30363d;
      border-left: 4px solid #58a6ff; border-radius: 8px;
      padding: 40px; max-width: 480px; width: 100%; text-align: center; }}
    h1 {{ color: #e6edf3; font-size: 1.4rem; margin-bottom: 8px; }}
    p {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 24px; line-height: 1.6; }}
    .spec-id {{ font-family: monospace; font-size: 0.8rem; color: #58a6ff;
      background: rgba(88,166,255,0.1); padding: 4px 10px; border-radius: 4px;
      display: inline-block; margin-bottom: 20px; }}
    .btn {{ display: inline-block; background: #238636; color: #fff;
      text-decoration: none; padding: 12px 28px; border-radius: 8px;
      font-weight: 600; font-size: 0.95rem; transition: opacity 0.15s; }}
    .btn:hover {{ opacity: 0.85; }}
    .note {{ margin-top: 20px; font-size: 0.8rem; color: #6e7681; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>🔒 PL Authentication Required</h1>
    <div class="spec-id">{spec_id[:8].upper()}...</div>
    <p>This UAT was created via the spec-first system and requires Product Lead
    authentication to view and record results.</p>
    <a class="btn" href="{login_url}">Sign in with Google</a>
    <div class="note">Access restricted to cprator@cbsware.com</div>
  </div>
</body>
</html>"""


def _render_unauthorized(email: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Unauthorized</title>
<style>body{{font-family:sans-serif;background:#0f1117;color:#c9d1d9;
  display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#161b22;border:1px solid #f85149;border-radius:8px;padding:40px;
  max-width:400px;text-align:center}}</style></head>
<body><div class="card">
<h1 style="color:#f85149">Unauthorized</h1>
<p>Signed in as <strong>{email}</strong></p>
<p style="color:#8b949e">PL access is restricted to cprator@cbsware.com.</p>
<a href="/app/logout" style="color:#58a6ff">Sign out</a>
</div></body></html>"""


def _render_oauth_not_configured() -> str:
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>OAuth Not Configured</title>
<style>body{font-family:sans-serif;background:#0f1117;color:#c9d1d9;
  display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:#161b22;border:1px solid #d29922;border-radius:8px;padding:40px;
  max-width:400px;text-align:center}</style></head>
<body><div class="card">
<h1 style="color:#d29922">OAuth Not Configured</h1>
<p style="color:#8b949e">GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set.<br>
Contact the system administrator.</p>
</div></body></html>"""
