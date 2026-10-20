# Fakes determinísticos de ms-agenda y ms-citas para evals/pytest SIN red.
# Semántica idéntica al HTTP real (contratos §4): éxito -> payload dict;
# error -> ToolError(status, code, message) que ejecutar_tool traduce a ok=False.
from typing import Any

from app.tools import ToolError

FILAS = [
    "08:00",
    "08:30",
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
    "13:00",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
    "15:30",
    "16:00",
    "16:30",
]

MEDICOS = [
    {
        "id": "11111111-1111-4111-8111-111111111111",
        "nombre": "Dra. Quispe",
        "especialidad": "PEDIATRIA",
        "activo": True,
    },
    {
        "id": "22222222-2222-4222-8222-222222222222",
        "nombre": "Dr. Ramos",
        "especialidad": "MEDICINA_GENERAL",
        "activo": True,
    },
    {
        "id": "33333333-3333-4333-8333-333333333333",
        "nombre": "Dra. Ayala",
        "especialidad": "MEDICINA_GENERAL",
        "activo": True,
    },
    {
        "id": "44444444-4444-4444-8444-444444444444",
        "nombre": "Dr. Huamán",
        "especialidad": "ODONTOLOGIA",
        "activo": True,
    },
    {
        "id": "55555555-5555-4555-8555-555555555555",
        "nombre": "Dra. Solano",
        "especialidad": "ODONTOLOGIA",
        "activo": True,
    },
]


class FakeCitaStore:
    """citas_db falsa: idempotencia (D1) + índice único parcial (RF-4)."""

    def __init__(self):
        self.citas: dict[str, dict[str, Any]] = {}
        self.idem: dict[str, str] = {}  # idempotency_key -> cita_id
        self._n = 0

    def crear(
        self, idem_key: str, paciente: dict, medico_id: str, fecha: str, hora: str
    ) -> dict:
        if idem_key in self.idem:
            return {"cita": self._limpio(self.citas[self.idem[idem_key]])}  # replay D1
        for cita in self.citas.values():
            if cita["estado"] == "CONFIRMADA" and (
                cita["medico_id"],
                cita["fecha"],
                cita["hora"],
            ) == (medico_id, fecha, hora):
                raise ToolError(409, "HORARIO_OCUPADO", "La franja ya está reservada")
        if fecha < "2026-10-20":
            raise ToolError(422, "VALIDACION", "No se aceptan fechas pasadas")
        self._n += 1
        cita_id = f"cita-{self._n:04d}"
        cita = {
            "id": cita_id,
            "estado": "CONFIRMADA",
            "medico_id": medico_id,
            "fecha": fecha,
            "hora": hora,
            "paciente_nombre": paciente["nombre"],
            "documento": paciente["documento"],
        }
        self.citas[cita_id] = cita
        self.idem[idem_key] = cita_id
        return {"cita": dict(cita)}

    def cancelar(self, cita_id: str) -> dict:
        cita = self.citas.get(cita_id)
        if not cita:
            raise ToolError(404, "CITA_NO_ENCONTRADA", "La cita no existe")
        if cita["estado"] == "CANCELADA":
            raise ToolError(409, "YA_CANCELADA", "La cita ya estaba cancelada")
        cita["estado"] = "CANCELADA"
        return {"cita": dict(cita)}

    def listar(self, documento: str) -> dict:
        items = [dict(c) for c in self.citas.values() if c["documento"] == documento]
        items.sort(key=lambda c: (c["fecha"], c["hora"]))
        return {"items": items, "page": 1, "size": 10, "total": len(items)}

    @staticmethod
    def _limpio(cita: dict) -> dict:
        return dict(cita)


def crear_fakes(store: FakeCitaStore) -> dict[str, Any]:
    def listar_medicos() -> list:
        return MEDICOS

    def ver_disponibilidad(medico_id: str, fecha: str) -> dict:
        if not next((m for m in MEDICOS if m["id"] == medico_id), None):
            raise ToolError(404, "MEDICO_NO_ENCONTRADO", "Médico inexistente")
        franjas = (
            [{"inicio": h, "fin": _fin(h), "disponible": True} for h in FILAS]
            if _es_laboral(fecha)
            else []
        )
        return {"medico_id": medico_id, "fecha": fecha, "franjas": franjas}

    def reservar_cita(paciente: dict, medico_id: str, fecha: str, hora: str) -> dict:
        import uuid as _uuid

        # fakes: key de idempotencia nueva por intento (como el agente real)
        return store.crear(str(_uuid.uuid4()), paciente, medico_id, fecha, hora)

    def cancelar_cita(cita_id: str) -> dict:
        return store.cancelar(cita_id)

    def listar_citas(documento: str) -> dict:
        return store.listar(documento)

    return {
        "listar_medicos": listar_medicos,
        "ver_disponibilidad": ver_disponibilidad,
        "reservar_cita": reservar_cita,
        "cancelar_cita": cancelar_cita,
        "listar_citas": listar_citas,
    }


def _es_laboral(fecha: str) -> bool:
    # D6: L-V laborables (seed). 2026-11-07/08 = sábado/domingo sin franjas.
    import datetime as dt

    return dt.date.fromisoformat(fecha).weekday() < 5


def _fin(inicio: str) -> str:
    h, m = inicio.split(":")
    mm = int(m) + 30
    if mm == 60:
        return f"{int(h) + 1:02d}:00"
    return f"{h}:{mm:02d}"
