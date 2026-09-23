from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.errors import forbidden
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.usuario import Usuario
from app.realtime.hub import broadcast
from app.schemas.announcement import AnnouncementIn, AnnouncementOut
from app.services.horarios import LA_PAZ

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

# Un anuncio por vez, en memoria: se borra solo al reiniciar el servicio.
_current: dict[str, str] | None = None

_VACIO: dict[str, str | None] = {"message": None, "author": None, "at": None}


def _actual() -> dict[str, str | None]:
    return dict(_current) if _current else dict(_VACIO)


@router.get("", response_model=AnnouncementOut)
def get_announcement():
    return _actual()


@router.post("", response_model=AnnouncementOut)
async def post_announcement(dto: AnnouncementIn, db: DbSession, user: CurrentUser):
    global _current
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede publicar anuncios")
    actual = db.get(Usuario, user.id)
    if actual is None or (actual.role != "Jefe" and not actual.can_view_dashboard):
        raise forbidden("Solo Jefe puede publicar anuncios")
    # Publicar reemplaza el anterior; mandar vacío lo borra.
    mensaje = dto.message.strip() if dto.message and dto.message.strip() else None
    if mensaje is None:
        _current = None
    else:
        _current = {
            "message": mensaje,
            "author": actual.display_name,
            "at": datetime.now(UTC).astimezone(LA_PAZ).strftime("%H:%M"),
        }
    await broadcast({"type": "receive_announcement", **_actual()})
    return _actual()
