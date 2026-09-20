from fastapi import APIRouter
from sqlalchemy import select

from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.area import Area
from app.models.grupo import Grupo
from app.models.grupo_padre import GrupoPadre
from app.schemas.jerarquia import ArbolOut, AreaOut, GrupoOut, GrupoPadreOut

router = APIRouter(prefix="/api/jerarquia", tags=["jerarquia"])


@router.get("/grupos-padres", response_model=list[GrupoPadreOut])
def get_grupos_padres(db: DbSession, user: CurrentUser):
    return db.scalars(select(GrupoPadre).order_by(GrupoPadre.orden)).all()


@router.get("/grupos", response_model=list[GrupoOut])
def get_grupos(db: DbSession, user: CurrentUser, grupo_padre_id: int | None = None):
    q = select(Grupo)
    if grupo_padre_id is not None:
        q = q.where(Grupo.grupo_padre_id == grupo_padre_id)
    return db.scalars(q.order_by(Grupo.nombre)).all()


@router.get("/areas", response_model=list[AreaOut])
def get_areas(
    db: DbSession,
    user: CurrentUser,
    grupo_padre_id: int | None = None,
    grupo_id: int | None = None,
):
    q = select(Area).where(Area.activo.is_(True))
    if grupo_padre_id is not None:
        q = q.where(Area.grupo_padre_id == grupo_padre_id)
    if grupo_id is not None:
        q = q.where(Area.grupo_id == grupo_id)
    return db.scalars(q.order_by(Area.nombre)).all()


@router.get("/arbol", response_model=ArbolOut)
def get_arbol(db: DbSession, user: CurrentUser):
    padres = db.scalars(select(GrupoPadre).order_by(GrupoPadre.orden)).all()
    grupos = db.scalars(select(Grupo).order_by(Grupo.nombre)).all()
    areas = db.scalars(
        select(Area).where(Area.activo.is_(True)).order_by(Area.nombre)
    ).all()
    return {"padres": padres, "grupos": grupos, "areas": areas}
