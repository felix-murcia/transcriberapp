"""
Rutas de autenticación OAuth2 para TranscriberApp
Similar a cine-platform
"""
import os
import secrets
import base64
import json
import hashlib
from urllib.parse import urlencode
from fastapi import APIRouter, Request, HTTPException, status, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from transcriber_app.modules.logging.logging_config import setup_logging

logger = setup_logging("transcribeapp")

router = APIRouter(prefix="", tags=["auth"])

# Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "templates"))


# Modelos
class TokenRequest(BaseModel):
    code: str
    code_verifier: str


# Variables de entorno OAuth2
def get_oauth_config():
    """Obtiene configuración OAuth2 del entorno"""
    return {
        "oauth2_url": os.environ.get("PUBLIC_OAUTH2_URL", "http://localhost:8080").rstrip("/"),
        "oauth2_internal_url": os.environ.get("OAUTH2_URL", "http://localhost:8080").rstrip("/"),
        "client_id": os.environ.get("OAUTH2_CLIENT_ID", "transcriberapp"),
        "client_secret": os.environ.get("OAUTH2_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("PUBLIC_REDIRECT_URI", "http://localhost:9000/oauth/callback"),
        "token_endpoint": os.environ.get("OAUTH2_TOKEN_ENDPOINT", "/oauth/token"),
        "userinfo_endpoint": os.environ.get("OAUTH2_USERINFO_ENDPOINT", "/user/me"),
    }


def generate_code_verifier() -> str:
    """Genera un code_verifier aleatorio (43-128 caracteres)"""
    random_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")
    return verifier


def generate_code_challenge(verifier: str) -> str:
    """Genera un code_challenge a partir del code_verifier usando SHA-256"""
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return challenge


@router.get("/login")
async def login_page(request: Request):
    """Página de login con OAuth2"""
    # Verificar si ya está autenticado
    if request.cookies.get("logged_in"):
        return RedirectResponse(url="/", status_code=302)

    config = get_oauth_config()
    
    return TEMPLATES.TemplateResponse(
        "login.html",
        {
            "request": request,
            "oauth2_url": config["oauth2_url"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
        },
    )


@router.post("/api/auth/oauth2/start")
async def start_oauth2_flow(request: Request):
    """
    Inicia el flujo OAuth2. Genera code_verifier, guarda en sesión y devuelve la URL de autorización.
    """
    try:
        # Verificar que no hay sesión activa
        if request.cookies.get("logged_in"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Ya hay una sesión activa"},
            )

        # Generar code_verifier y code_challenge
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)

        # Generar state aleatorio
        state = secrets.token_urlsafe(16)

        # Obtener configuración
        config = get_oauth_config()

        # Construir URL de autorización
        params = {
            "response_type": "code",
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": "openid profile read write",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "prompt": "login",
        }

        auth_url = f"{config['oauth2_url']}/oauth2/authorize?{urlencode(params)}"
        logger.info(f"[OAUTH_START] URL de autorización: {auth_url[:100]}...")

        # Guardar code_verifier en cookie (temporal)
        response = JSONResponse(
            content={
                "success": True,
                "authorization_url": auth_url,
            }
        )

        # Guardar code_verifier en cookie segura
        response.set_cookie(
            key="oauth_code_verifier",
            value=code_verifier,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=300,  # 5 minutos
        )

        response.set_cookie(
            key="oauth_state",
            value=state,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=300,
        )

        return response

    except Exception as e:
        logger.error(f"[OAUTH_START] Error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/oauth/callback")
async def oauth_callback(request: Request):
    """
    Callback de OAuth2 - Recibe la redirección del servidor OAuth2 con el código
    """
    try:
        code = request.query_params.get("code")
        error = request.query_params.get("error")
        error_description = request.query_params.get("error_description")
        state = request.query_params.get("state")

        if error:
            logger.warning(f"[OAUTH_CALLBACK] Error de OAuth2: {error} - {error_description}")
            return TEMPLATES.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": error + (f": {error_description}" if error_description else ""),
                },
            )

        if not code:
            logger.warning("[OAUTH_CALLBACK] Código faltante")
            return TEMPLATES.TemplateResponse(
                "login.html",
                {"request": request, "error": "Código de autorización faltante"},
            )

        # Obtener code_verifier desde cookie
        code_verifier = request.cookies.get("oauth_code_verifier")
        saved_state = request.cookies.get("oauth_state")

        if not code_verifier:
            logger.warning("[OAUTH_CALLBACK] Code verifier faltante")
            return TEMPLATES.TemplateResponse(
                "login.html",
                {"request": request, "error": "Code verifier faltante. Intenta de nuevo."},
            )

        # Verificar state
        if state and saved_state and state != saved_state:
            logger.warning("[OAUTH_CALLBACK] State mismatch")
            return TEMPLATES.TemplateResponse(
                "login.html",
                {"request": request, "error": "State mismatch - posible ataque CSRF"},
            )

        # Intercambiar código por token
        config = get_oauth_config()
        
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Intercambiar código por token
            token_response = await client.post(
                f"{config['oauth2_internal_url']}{config['token_endpoint']}",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": config["redirect_uri"],
                    "code_verifier": code_verifier,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {base64.b64encode(f'{config['client_id']}:{config['client_secret']}'.encode()).decode()}",
                },
            )

            if token_response.status_code != 200:
                logger.error(f"[OAUTH_CALLBACK] Error intercambiando código: {token_response.text}")
                return TEMPLATES.TemplateResponse(
                    "login.html",
                    {"request": request, "error": "Error al intercambiar código por token"},
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Obtener información del usuario
            userinfo_response = await client.get(
                f"{config['oauth2_internal_url']}{config['userinfo_endpoint']}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                logger.warning(f"[OAUTH_CALLBACK] Error obteniendo userinfo: {userinfo_response.status_code}")
                user_info = {}
            else:
                user_info = userinfo_response.json()

        # Crear respuesta con cookies de sesión
        response = RedirectResponse(url="/", status_code=302)

        # Cookies de sesión
        response.set_cookie(key="logged_in", value="true", httponly=True, secure=False, samesite="lax", max_age=86400)
        response.set_cookie(key="user_id", value=str(user_info.get("sub", 1)), httponly=True, secure=False, samesite="lax", max_age=86400)
        response.set_cookie(key="email", value=user_info.get("email", ""), httponly=True, secure=False, samesite="lax", max_age=86400)
        response.set_cookie(key="username", value=user_info.get("preferred_username", user_info.get("name", "user")), httponly=True, secure=False, samesite="lax", max_age=86400)
        response.set_cookie(key="user_role", value="admin", httponly=True, secure=False, samesite="lax", max_age=86400)

        # Limpiar cookies temporales
        response.delete_cookie("oauth_code_verifier")
        response.delete_cookie("oauth_state")

        logger.info(f"[OAUTH_CALLBACK] Login exitoso para: {user_info.get('username', 'user')}")

        return response

    except Exception as e:
        logger.error(f"[OAUTH_CALLBACK] Error: {e}", exc_info=True)
        return TEMPLATES.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Error: {str(e)}"},
        )


@router.get("/api/auth/check")
async def check_auth(request: Request):
    """Verifica el estado de autenticación"""
    logged_in = request.cookies.get("logged_in")

    if logged_in:
        return {
            "logged_in": True,
            "user_id": request.cookies.get("user_id"),
            "email": request.cookies.get("email"),
            "username": request.cookies.get("username"),
        }
    else:
        return {"logged_in": False}


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """Cierra sesión"""
    response = JSONResponse(content={"success": True})
    response.delete_cookie("logged_in")
    response.delete_cookie("user_id")
    response.delete_cookie("email")
    response.delete_cookie("username")
    response.delete_cookie("user_role")
    response.delete_cookie("oauth_code_verifier")
    response.delete_cookie("oauth_state")
    
    logger.info("[LOGOUT] Sesión cerrada")
    return response


@router.get("/status")
async def status_endpoint():
    """Estado de la API"""
    return {"status": "ok"}
