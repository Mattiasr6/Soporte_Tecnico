from fastapi import APIRouter

from app.core.errors import forbidden
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.usuario import Usuario
from app.schemas.announcement import AnnouncementIn, AnnouncementOut

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

_current: str | None = None


@router.get("", response_model=AnnouncementOut)
def get_announcement():
    return {"message": _current}


@router.post("", response_model=AnnouncementOut)
def post_announcement(dto: AnnouncementIn, db: DbSession, user: CurrentUser):
    global _current
    if not is_privileged(user):
        raise forbidden("Solo Jefe puede publicar anuncios")
    actual = db.get(Usuario, user.id)
    if actual is None or (actual.role != "Jefe" and not actual.can_view_dashboard):
        raise forbidden("Solo Jefe puede publicar anuncios")
    mensaje = dto.message.strip() if dto.message and dto.message.strip() else None
    _current = mensaje
    # TODO(S7): broadcast ReceiveAnnouncement
    return {"message": mensaje}
