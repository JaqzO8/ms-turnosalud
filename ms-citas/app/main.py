import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time
from typing import Annotated
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from .agenda import AgendaClient, BusinessError
from .auth import install_auth, user_for
from .db import Cita, make_engine
from .schemas import CitaResponse, Documento, ErrorResponse, Pagina, Reserva

logger = logging.getLogger(__name__)


def serialize(cita):
    return {
        "id": cita.id,
        "estado": cita.estado,
        "medico_id": cita.medico_id,
        "fecha": cita.fecha.isoformat(),
        "hora": cita.hora.strftime("%H:%M"),
        "paciente_nombre": cita.paciente_nombre,
        "documento": cita.documento,
    }


def replay(cita, digest):
    if cita.payload_hash != digest:
        raise BusinessError(409, "IDEMPOTENCIA_CONFLICTO", "La clave ya se utilizó con otros datos.")
    return JSONResponse(cita.respuesta_original, status_code=200)


def create_app(engine=None, agenda=None, clock=None, require_auth=True):
    owns_engine = engine is None
    engine = engine if engine is not None else make_engine()
    clock = clock or (lambda: datetime.now(ZoneInfo("America/Lima")))
    http_client = None
    if agenda is None:
        http_client = httpx.Client(
            base_url=os.getenv("AGENDA_URL", "http://localhost:3001"),
            timeout=float(os.getenv("AGENDA_TIMEOUT_SECONDS", "3")),
        )
        agenda = AgendaClient(http_client)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if http_client is not None:
            http_client.close()
        if owns_engine:
            engine.dispose()

    errors = {s: {"model": ErrorResponse} for s in (404, 409, 422, 503)}
    app = FastAPI(title="Turno-Salud: ms-citas", version="0.1.0", lifespan=lifespan, responses=errors)
    install_auth(app, engine)

    @app.middleware("http")
    async def correlation(request, call_next):
        supplied = request.headers.get("X-Correlation-ID", "")
        try:
            request.state.correlation_id = str(UUID(supplied))
        except ValueError:
            request.state.correlation_id = str(uuid4())
        request.state.user = None
        if require_auth and request.url.path.startswith("/api/v1/citas"):
            try:
                request.state.user = user_for(request, engine)
            except BusinessError as exc:
                return error(request, exc.status, exc.code, exc.message)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    def error(request, status, code, message):
        cid = getattr(request.state, "correlation_id", str(uuid4()))
        return JSONResponse(
            {
                "status": status,
                "code": code,
                "message": message,
                "correlation_id": cid,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=status,
            headers={"X-Correlation-ID": cid},
        )

    @app.exception_handler(BusinessError)
    async def business_error(request, exc):
        return error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(request, 422, "VALIDACION", "Revise campos, formatos y parámetros obligatorios.")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return error(request, 503, "BD_NO_DISPONIBLE", "No se pudo completar la operación.")

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.error("Error interno correlation_id=%s tipo=%s", request.state.correlation_id, type(exc).__name__)
        return error(request, 500, "ERROR_INTERNO", "Error interno del servicio.")

    @app.get("/health")
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.post(
        "/api/v1/citas",
        status_code=201,
        response_model=CitaResponse,
        responses={200: {"model": CitaResponse, "description": "Replay idempotente"}},
    )
    def reservar(body: Reserva, request: Request, idempotency_key: Annotated[UUID, Header()]):
        if request.state.user and body.paciente.documento != request.state.user["documento"]:
            raise BusinessError(403, "ACCESO_DENEGADO", "Solo puedes reservar tus propias citas.")
        digest = hashlib.sha256(
            json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        key = str(idempotency_key)
        with Session(engine) as session:
            existing = session.scalar(select(Cita).where(Cita.idempotency_key == key))
            if existing:
                return replay(existing, digest)
            # End the read transaction before remote IO and concurrent inserts.
            session.rollback()
            if body.fecha < clock().date():
                raise BusinessError(422, "VALIDACION", "La fecha no puede estar en el pasado.")
            agenda.validate(body, request.state.correlation_id)
            cita = Cita(
                id=str(uuid4()),
                medico_id=str(body.medico_id),
                fecha=body.fecha,
                hora=time.fromisoformat(body.hora),
                estado="CONFIRMADA",
                paciente_nombre=body.paciente.nombre,
                documento=body.paciente.documento,
                idempotency_key=key,
                payload_hash=digest,
            )
            cita.respuesta_original = {"cita": serialize(cita)}
            session.add(cita)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(select(Cita).where(Cita.idempotency_key == key))
                if existing:
                    return replay(existing, digest)
                occupied = session.scalar(
                    select(Cita).where(
                        Cita.medico_id == str(body.medico_id),
                        Cita.fecha == body.fecha,
                        Cita.hora == time.fromisoformat(body.hora),
                        Cita.estado == "CONFIRMADA",
                    )
                )
                if occupied:
                    raise BusinessError(
                        409, "HORARIO_OCUPADO", "Ya existe una cita confirmada en ese horario."
                    ) from None
                raise
            return cita.respuesta_original

    @app.post("/api/v1/citas/{cita_id}/cancelar", response_model=CitaResponse)
    def cancelar(cita_id: UUID, request: Request):
        with Session(engine) as session:
            owned = session.get(Cita, str(cita_id))
            if request.state.user and (not owned or owned.documento != request.state.user["documento"]):
                raise BusinessError(404, "CITA_NO_ENCONTRADA", "La cita no existe.")
            result = session.execute(
                update(Cita).where(Cita.id == str(cita_id), Cita.estado == "CONFIRMADA").values(estado="CANCELADA")
            )
            if result.rowcount == 0:
                existing = session.get(Cita, str(cita_id))
                if existing is None:
                    raise BusinessError(404, "CITA_NO_ENCONTRADA", "La cita no existe.")
                raise BusinessError(409, "CITA_YA_CANCELADA", "La cita ya fue cancelada.")
            session.commit()
            return {"cita": serialize(session.get(Cita, str(cita_id)))}

    @app.get("/api/v1/citas", response_model=Pagina)
    def listar(
        request: Request,
        documento: Documento,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 10,
    ):
        if request.state.user and documento != request.state.user["documento"]:
            raise BusinessError(403, "ACCESO_DENEGADO", "Solo puedes consultar tus propias citas.")
        with Session(engine) as session:
            total = session.scalar(select(func.count()).select_from(Cita).where(Cita.documento == documento))
            citas = session.scalars(
                select(Cita)
                .where(Cita.documento == documento)
                .order_by(Cita.fecha, Cita.hora, Cita.id)
                .offset((page - 1) * size)
                .limit(size)
            )
            return {"items": [serialize(c) for c in citas], "page": page, "size": size, "total": total}

    return app
