# Eval suite (tests E2E del agente): E-01..E-07, corren contra el sistema
# según el plan y su seed (D6): FIXED_TODAY = lunes 2026-11-02.
# E-02 (anti doble reserva) y E-07 (multi-turno) usan rondas repetidas/mismo
# horario de sesión; se evalúa SIEMPRE el resultado de la ÚLTIMA ronda.
from typing import Any, Callable


class Eval:
    def __init__(self, id_: str, prompts: list[str], esperado: Callable[[dict[str, Any]], tuple[bool, str]],
                 misma_sesion: bool = False):
        self.id = id_
        self.prompts = prompts
        self.esperado = esperado
        self.misma_sesion = misma_sesion


def _reserva_exitosa(r: dict[str, Any]) -> tuple[bool, str]:
    reservas = [t for t in r["tools_usadas"] if t["name"] == "reservar_cita"]
    if reservas and reservas[0]["ok"] and "CONFIRMADA" in r["respuesta"]:
        return True, "reservar_cita ok + CONFIRMADA en respuesta"
    if reservas and reservas[0]["ok"]:
        return False, "reservó pero no confirmó en la respuesta"
    return False, f"no reservó (tools={[(t['name'], t.get('code')) for t in r['tools_usadas']]})"


def _reserva_rehusada_alternativas(r: dict[str, Any]) -> tuple[bool, str]:
    reservas = [t for t in r["tools_usadas"] if t["name"] == "reservar_cita"]
    if any(t["ok"] for t in reservas):
        return False, "reservó de nuevo cuando debía rehusar"
    if any(t["name"] == "ver_disponibilidad" for t in r["tools_usadas"]):
        return True, "consultó disponibilidad, rehusó la franja ocupada y dio alternativas"
    return False, f"no consultó disponibilidad (tools={[t['name'] for t in r['tools_usadas']]})"


def _especialidad_no_atendida(r: dict[str, Any]) -> tuple[bool, str]:
    if any(t["name"] == "reservar_cita" for t in r["tools_usadas"]):
        return False, "intentó reservar para especialidad sin médico"
    if any(t["name"] == "listar_medicos" for t in r["tools_usadas"]):
        return True, "listó médicos y no reservó (respuesta honesta)"
    if not r["tools_usadas"]:
        return True, "pidió aclarar especialidad (datos incompletos), sin reservar"
    return False, f"comportamiento inesperado (tools={[t['name'] for t in r['tools_usadas']]})"


def _cancelado(r: dict[str, Any]) -> tuple[bool, str]:
    if any(t["name"] == "cancelar_cita" and t["ok"] for t in r["tools_usadas"]):
        return True, "canceló la cita activa"
    return False, f"no canceló (tools={[(t['name'], t.get('code')) for t in r['tools_usadas']]})"


def _fuera_dominio(r: dict[str, Any]) -> tuple[bool, str]:
    if r["tools_usadas"]:
        return False, "llamó a tools en un tema fuera de dominio"
    if "cita" in r["respuesta"].lower():
        return True, "respondió sin tools, redirigiendo al dominio"
    return False, "respuesta sin redirección al dominio"


def _datos_incompletos_pregunta(r: dict[str, Any]) -> tuple[bool, str]:
    if r["tools_usadas"]:
        return False, "llamó a tools con datos incompletos (debería PREGUNTAR)"
    resp = r["respuesta"].lower()
    if "?" in resp and any(k in resp for k in ("especialidad", "fecha", "hora", "documento")):
        return True, "preguntó por el dato faltante sin tocar tools"
    return False, "no preguntó por el dato faltante"


EVALS = [
    # D6: jueves = 2026-11-05 (franja pediatría 10:00 libre al iniciar)
    Eval(
        "E-01",
        ["Soy María Flores, documento 12345678. Quiero una cita con pediatría el 2026-11-05 a las 10."],
        _reserva_exitosa,
    ),
    Eval(
        "E-02",
        # 2 rondas iguales: la 1ª reserva odontología lunes 08:00; la 2ª debe rehusar (409)
        [
            "Soy Rosa Ttito, documento 99887766. Quiero cita con odontología el 2026-11-02 a las 08.",
            "Soy Rosa Ttito, documento 99887766. Quiero cita con odontología el 2026-11-02 a las 08.",
        ],
        _reserva_rehusada_alternativas,
    ),
    Eval(
        "E-03",
        ["Soy Ana Quispe, documento 44445555. Quiero cita con cardiología."],
        _especialidad_no_atendida,
    ),
    Eval(
        "E-04",
        ["Documento 12345678. Quiero cancelar mi cita."],
        _cancelado,
    ),
    Eval("E-05", ["¿Qué clima hace hoy en Huánuco?"], _fuera_dominio),
    # E-06: datos incompletos -> el harness PREGUNTA (sin tools)
    Eval("E-06", ["Hola, quiero una cita."], _datos_incompletos_pregunta),
    # E-07: reserva multi-turno con memoria de sesión (misma sesión, 4 rondas)
    Eval(
        "E-07",
        [
            "Hola, necesito una cita.",
            "con odontología",
            "el 2026-11-03",
            "a las 09:30. Soy Ramiro Sedano, documento 55778899",
        ],
        _reserva_exitosa,
        misma_sesion=True,
    ),
]


def correr_evals(agente) -> list[dict[str, Any]]:
    resultados = []
    for e in EVALS:
        turno: dict[str, Any] | None = None
        for i, prompt in enumerate(e.prompts):
            sesion = f"eval-{e.id}" if e.misma_sesion else f"eval-{e.id}-r{i + 1}"
            turno = agente.responder(prompt, sesion_id=sesion)
        ok, detalle = e.esperado(turno)  # se evalúa la ÚLTIMA ronda
        resultados.append(
            {
                "id": e.id,
                "prompt": e.prompts[-1],
                "esperado": detalle,
                "obtenido": turno["respuesta"],
                "tools_usadas": turno["tools_usadas"],
                "ok": ok,
            }
        )
    return resultados
