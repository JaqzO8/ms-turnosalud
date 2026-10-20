from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Hora = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
Documento = Annotated[str, StringConstraints(pattern=r"^[0-9]{8}$")]


class Paciente(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nombre: str = Field(min_length=1, max_length=200)
    documento: Documento


class Reserva(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paciente: Paciente
    medico_id: UUID
    fecha: date
    hora: Hora


class CitaOut(BaseModel):
    id: UUID
    estado: Literal["CONFIRMADA", "CANCELADA"]
    medico_id: UUID
    fecha: date
    hora: Hora
    paciente_nombre: str
    documento: Documento


class CitaResponse(BaseModel):
    cita: CitaOut


class Pagina(BaseModel):
    items: list[CitaOut]
    page: int
    size: int
    total: int


class ErrorResponse(BaseModel):
    status: int
    code: str
    message: str
    correlation_id: str
    timestamp: str
