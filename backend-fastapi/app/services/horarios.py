"""Port de HorarioHelper .NET: cálculo de fuera-de-turno en America/La_Paz."""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

LA_PAZ = ZoneInfo("America/La_Paz")


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    try:
        hora, minuto = value.split(":")
        return time(int(hora), int(minuto))
    except ValueError:
        return None


def _dentro_de_bloques(
    inicio1: str | None,
    fin1: str | None,
    inicio2: str | None,
    fin2: str | None,
    hora: time,
) -> bool:
    for ini_raw, fin_raw in ((inicio1, fin1), (inicio2, fin2)):
        ini, fin = _parse_hhmm(ini_raw), _parse_hhmm(fin_raw)
        if ini is not None and fin is not None and ini <= hora <= fin:
            return True
    return False


def esta_fuera_de_horario(
    hora_inicio1: str | None,
    hora_fin1: str | None,
    hora_inicio2: str | None,
    hora_fin2: str | None,
    fecha_utc: datetime,
) -> bool:
    dt = fecha_utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    hora_local = dt.astimezone(LA_PAZ).timetz().replace(tzinfo=None)
    return not _dentro_de_bloques(
        hora_inicio1, hora_fin1, hora_inicio2, hora_fin2, hora_local
    )
