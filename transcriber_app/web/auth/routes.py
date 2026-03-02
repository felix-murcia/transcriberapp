"""
Rutas de autenticación para TranscriberApp
Blueprint para /api/auth y login
"""
from fastapi import APIRouter, Request, HTTPException, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from transcriber_app.modules.logging.logging_config import setup_logging
from .use_cases import get_login_use_case, get_logout_use_case
from .dependencies import (
    create_session,
    get_session,
    delete_session,
    get_current_user,
    is_authenticated,
    SESSIONS
)

logger = setup_logging("transcribeapp")

router = APIRouter(prefix="/auth", tags=["auth"])


# Modelos de request
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenRequest(BaseModel):
    token: str


@router.post("/login")
async def login(request: Request, response: Response, login_data: LoginRequest):
    """Endpoint de login"""
    logger.info(f"[API LOGIN] Intento de login para: {login_data.email}")
    
    login_use_case = get_login_use_case()
    success, user_data = login_use_case.execute(login_data.email, login_data.password)
    
    if success:
        # Crear sesión
        token = create_session(user_data.get("id"), user_data)
        
        # Configurar cookie de sesión
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=False,  # Cambiar a True en producción con HTTPS
            samesite="lax",
            max_age=86400  # 24 horas
        )
        
        logger.info(f"[API LOGIN] Login exitoso para: {login_data.email}")
        
        return {
            "success": True,
            "user": user_data
        }
    else:
        logger.warning(f"[API LOGIN] Credenciales incorrectas para: {login_data.email}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": "Credenciales inválidas"
            }
        )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Endpoint de logout"""
    token = request.cookies.get("session_token")
    
    if token:
        # Eliminar sesión
        delete_session(token)
        
        # Limpiar cookie
        response.delete_cookie("session_token")
        
        logger.info("[API LOGOUT] Logout exitoso")
        return {"success": True}
    
    return {"success": True}


@router.get("/check")
async def check_auth(request: Request):
    """Verifica el estado de autenticación"""
    user = get_current_user(request)
    
    if user:
        return {
            "logged_in": True,
            "user_id": user.get("id"),
            "email": user.get("email"),
            "username": user.get("username")
        }
    else:
        return {"logged_in": False}


@router.post("/token")
async def verify_token(request: Request, token_data: TokenRequest):
    """Verifica un token de autenticación"""
    login_use_case = get_login_use_case()
    user_data = login_use_case.verify_token(token_data.token)
    
    if user_data:
        return {
            "valid": True,
            "user": user_data
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"valid": False}
        )


@router.get("/session")
async def get_session_info(request: Request):
    """Obtiene información de la sesión actual"""
    token = request.cookies.get("session_token")
    
    if token:
        session = get_session(token)
        if session:
            return {
                "active": True,
                "user_id": session.get("user_id"),
                "user_data": session.get("user_data")
            }
    
    return {"active": False}
