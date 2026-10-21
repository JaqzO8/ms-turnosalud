import logging
import os

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app import tools
from app.config import CONFIG

logger = logging.getLogger("turnosalud.portal")


def remote(request, method, path, body=None, params=None):
    token = request.cookies.get("turnosalud_session", "")
    try:
        with httpx.Client(
            timeout=10, transport=tools._TRANSPORT, trust_env=False
        ) as client:
            result = client.request(
                method,
                CONFIG.MS_CITAS_URL + path,
                json=body,
                params=params,
                headers={"Authorization": "Bearer " + token},
            )
    except httpx.HTTPError as exc:
        logger.warning("citas inalcanzable: %r url=%s", exc, CONFIG.MS_CITAS_URL + path)
        raise HTTPException(503, "El servicio de citas no está disponible.") from None
    return result


def current_user(request):
    response = remote(request, "GET", "/auth/me")
    if response.status_code != 200:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return response.json()


def csrf(request):
    if request.headers.get("X-Requested-With") != "TurnoSalud":
        raise HTTPException(403, "Solicitud no permitida.")


def install_portal(app):
    @app.post("/portal/register")
    async def register(request: Request):
        csrf(request)
        result = remote(request, "POST", "/auth/register", await request.json())
        return JSONResponse(result.json(), status_code=result.status_code)

    @app.post("/portal/login")
    async def login(request: Request):
        csrf(request)
        result = remote(request, "POST", "/auth/login", await request.json())
        data = result.json()
        token = data.pop("token", None)
        response = JSONResponse(data, status_code=result.status_code)
        if token:
            response.set_cookie(
                "turnosalud_session",
                token,
                httponly=True,
                samesite="strict",
                max_age=28800,
                secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            )
        return response

    @app.post("/portal/logout")
    def logout(request: Request):
        csrf(request)
        remote(request, "POST", "/auth/logout")
        response = JSONResponse({"ok": True})
        response.delete_cookie("turnosalud_session")
        return response

    @app.get("/portal/me")
    def me(request: Request):
        return current_user(request)

    @app.get("/portal/citas")
    def citas(request: Request, page: int = 1):
        user = current_user(request)
        result = remote(
            request,
            "GET",
            "/api/v1/citas",
            params={"documento": user["documento"], "page": page, "size": 10},
        )
        return JSONResponse(result.json(), status_code=result.status_code)

    @app.post("/portal/citas/{cita_id}/cancelar")
    def cancel(cita_id: str, request: Request):
        csrf(request)
        current_user(request)
        result = remote(request, "POST", f"/api/v1/citas/{cita_id}/cancelar")
        return JSONResponse(result.json(), status_code=result.status_code)
