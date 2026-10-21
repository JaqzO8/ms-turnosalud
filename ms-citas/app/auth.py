import hashlib
import hmac
import secrets
import time

from fastapi import Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .agenda import BusinessError
from .db import Cita, LoginSession, Usuario
from .schemas import Documento


class Credentials(BaseModel):
    documento: Documento
    password: str = Field(min_length=8, max_length=128)


class Registration(Credentials):
    nombre: str = Field(min_length=1, max_length=200)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ":" + digest


def bearer(request):
    value = request.headers.get("Authorization", "")
    return value[7:] if value.startswith("Bearer ") else ""


def user_for(request, engine):
    token = bearer(request)
    with Session(engine) as session:
        login = session.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
        if not token or not login or login.expires <= int(time.time()):
            raise BusinessError(401, "NO_AUTORIZADO", "Inicia sesión para continuar.")
        user = session.get(Usuario, login.documento)
        return {"documento": user.documento, "nombre": user.nombre}


def install_auth(app, engine):
    @app.post("/auth/register", status_code=201)
    def register(body: Registration):
        with Session(engine) as session:
            # Legacy bookings cannot be claimed by merely knowing a document number.
            if session.get(Usuario, body.documento) or session.scalar(
                select(Cita.id).where(Cita.documento == body.documento).limit(1)
            ):
                raise BusinessError(
                    409,
                    "REGISTRO_NO_DISPONIBLE",
                    "Documento ya registrado o con citas previas. Contacta al administrador.",
                )
            name = body.nombre.strip()
            if not name:
                raise BusinessError(422, "VALIDACION", "Indica tu nombre.")
            session.add(Usuario(documento=body.documento, nombre=name, password_hash=hash_password(body.password)))
            try:
                session.commit()
            except IntegrityError:
                raise BusinessError(409, "REGISTRO_NO_DISPONIBLE", "Documento ya registrado.") from None
        return {"ok": True}

    @app.post("/auth/login")
    def login(body: Credentials):
        with Session(engine) as session:
            user = session.get(Usuario, body.documento)
            stored = user.password_hash if user else hash_password("invalid-password")
            computed = hash_password(body.password, stored.split(":")[0])
            if not user or not hmac.compare_digest(stored, computed):
                raise BusinessError(401, "CREDENCIALES_INVALIDAS", "Documento o contraseña incorrectos.")
            token = secrets.token_urlsafe(32)
            session.execute(delete(LoginSession).where(LoginSession.expires <= int(time.time())))
            session.add(
                LoginSession(
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    documento=user.documento,
                    expires=int(time.time()) + 28800,
                )
            )
            session.commit()
            return {"token": token, "usuario": {"nombre": user.nombre, "documento": user.documento}}

    @app.get("/auth/me")
    def me(request: Request):
        return user_for(request, engine)

    @app.post("/auth/logout")
    def logout(request: Request):
        with Session(engine) as session:
            session.execute(
                delete(LoginSession).where(
                    LoginSession.token_hash == hashlib.sha256(bearer(request).encode()).hexdigest()
                )
            )
            session.commit()
        return {"ok": True}
