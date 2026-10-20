from datetime import date
from uuid import UUID

import httpx
from pydantic import BaseModel, StrictBool, ValidationError

from .schemas import Hora


class BusinessError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


class Franja(BaseModel):
    inicio: Hora
    fin: Hora
    disponible: StrictBool


class Disponibilidad(BaseModel):
    medico_id: UUID
    fecha: date
    franjas: list[Franja]


class AgendaClient:
    def __init__(self, client):
        self.client = client

    def validate(self, reserva, correlation_id):
        try:
            response = self.client.get(
                f"/api/v1/medicos/{reserva.medico_id}/disponibilidad",
                params={"fecha": reserva.fecha.isoformat()},
                headers={"X-Correlation-ID": correlation_id},
            )
            if response.status_code in (400, 404):
                raise BusinessError(422, "VALIDACION", "Médico o fecha no válidos en agenda.")
            response.raise_for_status()
            data = Disponibilidad.model_validate(response.json())
            if data.medico_id != reserva.medico_id or data.fecha != reserva.fecha:
                raise ValueError("Agenda devolvió otra consulta")
        except (httpx.HTTPError, ValidationError, ValueError) as exc:
            raise BusinessError(
                503, "AGENDA_NO_DISPONIBLE", "No se pudo validar la agenda; reintente más tarde."
            ) from exc
        slot = next((f for f in data.franjas if f.inicio == reserva.hora), None)
        if slot is None:
            raise BusinessError(422, "VALIDACION", "Hora fuera de las franjas del médico.")
        if not slot.disponible:
            raise BusinessError(409, "HORARIO_OCUPADO", "El horario no está disponible.")
