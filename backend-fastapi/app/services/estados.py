"""Port de HorarioHelper.EstadoEfectivo .NET. Puro, sin DB."""

from datetime import datetime

from app.models.horario import Horario
from app.services.horarios import esta_fuera_de_horario


def estado_efectivo(
    estado_actual: str, horario: Horario | None, ahora_utc: datetime
) -> str:
    if estado_actual == "Ausente":
        return "ausente"
    if estado_actual == "Extraturno":
        return "extraturno"
    if estado_actual in ("Disponible", "Ocupado"):
        if horario is None:
            return "extraturno"
        if esta_fuera_de_horario(
            horario.hora_inicio1,
            horario.hora_fin1,
            horario.hora_inicio2,
            horario.hora_fin2,
            ahora_utc,
        ):
            return "extraturno"
    return estado_actual.lower()
