"""
Primary adapters - Authentication routes.
"""

import os
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from transcriber_app.domain.ports import SessionManagerPort
from transcriber_app.infrastructure.auth import (
    get_session_manager,
    get_auth_service,
)
from transcriber_app.infrastructure.logging.logging_config import setup_logging

logger = setup_logging("transcribeapp")

router = APIRouter()

# Session manager (in-memory for now)
SESSION_MANAGER: SessionManagerPort = get_session_manager()

# Login page
LOGIN_HTML = Path(__file__).parent.parent.parent / "web" / "templates" / "login.html"


@router.get("/login")
async def login_page(request: Request):
    """Serve login page."""
    if LOGIN_HTML.exists():
        return FileResponse(LOGIN_HTML)
    return HTMLResponse(content="Login page not found", status_code=404)


@router.post("/login")
async def login(request: Request):
    """Handle login request."""
    # This is a simplified version - actual implementation would use auth service
    from fastapi import Form
    username = (await request.form()).get("username", "")
    password = (await request.form()).get("password", "")

    service = get_auth_service()

    try:
        result = service.authenticate(username, password)
        if result and result.get("success"):
            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(key="logged_in", value="true")
            response.set_cookie(key="username", value=username)
            logger.info(f"[AUTH] Login successful for: {username}")
            return response
    except Exception as e:
        logger.error(f"[AUTH] Login failed for {username}: {e}")

    return HTMLResponse(content="Login failed", status_code=401)


@router.post("/oauth/callback")
async def oauth_callback(request: Request):
    """Handle OAuth callback."""
    # Placeholder for OAuth implementation
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="logged_in", value="true")
    return response


@router.post("/logout")
async def logout(request: Request):
    """Handle logout."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="logged_in")
    response.delete_cookie(key="username")
    logger.info("[AUTH] User logged out")
    return response
