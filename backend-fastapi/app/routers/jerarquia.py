from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.errors import bad_request, forbidden, not_found
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.area import Area
from app.models.atencion import Atencion
from app.models.grupo import Grupo
from app.models.grupo_padre import GrupoPadre
from app.schemas.jerarquia import (
    ArbolOut,
    AreaConversionOut,
    AreaIn,
    AreaOut,
    AreaUpd,
    GrupoIn,
    GrupoOut,
    GrupoPadreIn,
    GrupoPadreOut,
    GrupoPadreUpd,
    GrupoUpd,
)
from app.services.slugs import codigo_unico, slugify

router = APIRouter(prefix="/api/jerarquia", tags=["jerarquia"])


def _exigir_jefe(user) -> None:
    if not is_privileged(user):
        raise forbidden("Solo un jefe puede administrar el catálogo")


def _texto(valor: str, campo: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise bad_request(f"{campo} no puede estar vacío")
    return limpio


def _codigo_libre(
    db: DbSession, modelo, base: str, actual_id: int | None = None
) -> str:
    usados = set(db.scalars(select(modelo.codigo)).all())
    if actual_id is not None:
        actual = db.get(modelo, actual_id)
        if actual is not None:
            usados.discard(actual.codigo)
    return codigo_unico(slugify(base) or "nodo", usados)


def _verificar_codigo(
    db: DbSession, modelo, codigo: str, actual_id: int | None = None
) -> str:
    limpio = slugify(codigo)
    if not limpio:
        raise bad_request("El código no puede estar vacío")
    q = select(modelo).where(modelo.codigo == limpio)
    if actual_id is not None:
        q = q.where(modelo.id != actual_id)
    if db.scalars(q).first() is not None:
        raise bad_request(f"El código '{limpio}' ya está en uso")
    return limpio


def _area_duplicada(
    db: DbSession,
    nombre: str,
    padre_id: int,
    grupo_id: int | None,
    actual_id: int | None = None,
) -> bool:
    q = select(Area).where(
        Area.nombre == nombre,
        Area.grupo_padre_id == padre_id,
        Area.grupo_id.is_(None) if grupo_id is None else Area.grupo_id == grupo_id,
    )
    if actual_id is not None:
        q = q.where(Area.id != actual_id)
    return db.scalars(q).first() is not None


def _atenciones_area(db: DbSession, area_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Atencion)
            .where(Atencion.area_id == area_id)
        )
        or 0
    )


def _propagar_area(db: DbSession, area: Area) -> int:
    """Re-apunta las atenciones del área a su sector y dependencia actuales.

    Las atenciones guardan copia de los 3 FK, así que sin esto el dashboard seguiría
    contando bajo el sector viejo.
    """
    filas = db.scalars(select(Atencion).where(Atencion.area_id == area.id)).all()
    for atencion in filas:
        atencion.grupo_padre_id = area.grupo_padre_id
        atencion.grupo_id = area.grupo_id
    return len(filas)


def _propagar_grupo(db: DbSession, grupo: Grupo) -> int:
    """Mover una dependencia arrastra sus áreas y re-apunta sus atenciones."""
    areas = db.scalars(select(Area).where(Area.grupo_id == grupo.id)).all()
    total = 0
    for area in areas:
        area.grupo_padre_id = grupo.grupo_padre_id
        total += _propagar_area(db, area)
    return total


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
    incluir_inactivas: bool = False,
):
    q = select(Area)
    if not incluir_inactivas:
        q = q.where(Area.activo.is_(True))
    if grupo_padre_id is not None:
        q = q.where(Area.grupo_padre_id == grupo_padre_id)
    if grupo_id is not None:
        q = q.where(Area.grupo_id == grupo_id)
    return db.scalars(q.order_by(Area.nombre)).all()


@router.get("/arbol", response_model=ArbolOut)
def get_arbol(db: DbSession, user: CurrentUser, incluir_inactivas: bool = False):
    areas_q = select(Area)
    grupos_q = select(Grupo)
    if not incluir_inactivas:
        areas_q = areas_q.where(Area.activo.is_(True))
        grupos_q = grupos_q.where(Grupo.activo.is_(True))
    return {
        "padres": db.scalars(select(GrupoPadre).order_by(GrupoPadre.orden)).all(),
        "grupos": db.scalars(grupos_q.order_by(Grupo.nombre)).all(),
        "areas": db.scalars(areas_q.order_by(Area.nombre)).all(),
    }


@router.post("/grupos-padres", response_model=GrupoPadreOut, status_code=201)
def crear_grupo_padre(dto: GrupoPadreIn, db: DbSession, user: CurrentUser):
    _exigir_jefe(user)
    nombre = _texto(dto.nombre, "El nombre")
    if db.scalars(select(GrupoPadre).where(GrupoPadre.nombre == nombre)).first():
        raise bad_request(f"Ya existe un sector llamado '{nombre}'")
    codigo = (
        _verificar_codigo(db, GrupoPadre, dto.codigo)
        if dto.codigo
        else _codigo_libre(db, GrupoPadre, nombre)
    )
    orden = dto.orden
    if orden is None:
        orden = (db.scalar(select(func.max(GrupoPadre.orden))) or 0) + 1
    padre = GrupoPadre(
        nombre=nombre, codigo=codigo, descripcion=dto.descripcion, orden=orden
    )
    db.add(padre)
    db.commit()
    db.refresh(padre)
    return padre


@router.put("/grupos-padres/{padre_id}", response_model=GrupoPadreOut)
def editar_grupo_padre(
    padre_id: int, dto: GrupoPadreUpd, db: DbSession, user: CurrentUser
):
    _exigir_jefe(user)
    padre = db.get(GrupoPadre, padre_id)
    if padre is None:
        raise not_found("Sector no encontrado")
    if dto.nombre is not None:
        nombre = _texto(dto.nombre, "El nombre")
        repetido = db.scalars(
            select(GrupoPadre).where(
                GrupoPadre.nombre == nombre, GrupoPadre.id != padre_id
            )
        ).first()
        if repetido:
            raise bad_request(f"Ya existe un sector llamado '{nombre}'")
        padre.nombre = nombre
    if dto.codigo is not None:
        padre.codigo = _verificar_codigo(db, GrupoPadre, dto.codigo, padre_id)
    if dto.descripcion is not None:
        padre.descripcion = dto.descripcion
    if dto.orden is not None:
        padre.orden = dto.orden
    db.commit()
    db.refresh(padre)
    return padre


@router.delete("/grupos-padres/{padre_id}", status_code=204)
def borrar_grupo_padre(padre_id: int, db: DbSession, user: CurrentUser) -> None:
    _exigir_jefe(user)
    padre = db.get(GrupoPadre, padre_id)
    if padre is None:
        raise not_found("Sector no encontrado")
    grupos = db.scalar(
        select(func.count()).select_from(Grupo).where(Grupo.grupo_padre_id == padre_id)
    )
    areas = db.scalar(
        select(func.count()).select_from(Area).where(Area.grupo_padre_id == padre_id)
    )
    atenciones = db.scalar(
        select(func.count())
        .select_from(Atencion)
        .where(Atencion.grupo_padre_id == padre_id)
    )
    if grupos or areas or atenciones:
        raise bad_request(
            f"'{padre.nombre}' tiene {grupos} dependencias, {areas} áreas y "
            f"{atenciones} atenciones: no se puede borrar."
        )
    db.delete(padre)
    db.commit()


@router.post("/grupos", response_model=GrupoOut, status_code=201)
def crear_grupo(dto: GrupoIn, db: DbSession, user: CurrentUser):
    _exigir_jefe(user)
    nombre = _texto(dto.nombre, "El nombre")
    if db.get(GrupoPadre, dto.grupo_padre_id) is None:
        raise bad_request(f"El sector {dto.grupo_padre_id} no existe")
    repetido = db.scalars(
        select(Grupo).where(
            Grupo.nombre == nombre, Grupo.grupo_padre_id == dto.grupo_padre_id
        )
    ).first()
    if repetido:
        raise bad_request(f"Ya existe una dependencia '{nombre}' en ese sector")
    codigo = (
        _verificar_codigo(db, Grupo, dto.codigo)
        if dto.codigo
        else _codigo_libre(db, Grupo, nombre)
    )
    grupo = Grupo(
        nombre=nombre,
        codigo=codigo,
        grupo_padre_id=dto.grupo_padre_id,
        activo=dto.activo,
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.put("/grupos/{grupo_id}", response_model=GrupoOut)
def editar_grupo(grupo_id: int, dto: GrupoUpd, db: DbSession, user: CurrentUser):
    _exigir_jefe(user)
    grupo = db.get(Grupo, grupo_id)
    if grupo is None:
        raise not_found("Dependencia no encontrada")

    nuevo_padre = grupo.grupo_padre_id
    if "grupo_padre_id" in dto.model_fields_set and dto.grupo_padre_id is not None:
        if db.get(GrupoPadre, dto.grupo_padre_id) is None:
            raise bad_request(f"El sector {dto.grupo_padre_id} no existe")
        nuevo_padre = dto.grupo_padre_id

    if dto.nombre is not None:
        nombre = _texto(dto.nombre, "El nombre")
        repetido = db.scalars(
            select(Grupo).where(
                Grupo.nombre == nombre,
                Grupo.grupo_padre_id == nuevo_padre,
                Grupo.id != grupo_id,
            )
        ).first()
        if repetido:
            raise bad_request(f"Ya existe una dependencia '{nombre}' en ese sector")
        grupo.nombre = nombre
    if dto.codigo is not None:
        grupo.codigo = _verificar_codigo(db, Grupo, dto.codigo, grupo_id)
    if dto.activo is not None:
        grupo.activo = dto.activo

    movido = nuevo_padre != grupo.grupo_padre_id
    grupo.grupo_padre_id = nuevo_padre
    if movido:
        _propagar_grupo(db, grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.delete("/grupos/{grupo_id}", status_code=204)
def borrar_grupo(grupo_id: int, db: DbSession, user: CurrentUser) -> None:
    _exigir_jefe(user)
    grupo = db.get(Grupo, grupo_id)
    if grupo is None:
        raise not_found("Dependencia no encontrada")
    areas = db.scalar(
        select(func.count()).select_from(Area).where(Area.grupo_id == grupo_id)
    )
    atenciones = db.scalar(
        select(func.count()).select_from(Atencion).where(Atencion.grupo_id == grupo_id)
    )
    if areas or atenciones:
        raise bad_request(
            f"'{grupo.nombre}' tiene {areas} áreas y {atenciones} atenciones: "
            "no se puede borrar."
        )
    db.delete(grupo)
    db.commit()


@router.post("/areas", response_model=AreaOut, status_code=201)
def crear_area(dto: AreaIn, db: DbSession, user: CurrentUser):
    _exigir_jefe(user)
    nombre = _texto(dto.nombre, "El nombre")
    if db.get(GrupoPadre, dto.grupo_padre_id) is None:
        raise bad_request(f"El sector {dto.grupo_padre_id} no existe")
    if dto.grupo_id is not None:
        grupo = db.get(Grupo, dto.grupo_id)
        if grupo is None:
            raise bad_request(f"La dependencia {dto.grupo_id} no existe")
        if grupo.grupo_padre_id != dto.grupo_padre_id:
            raise bad_request(
                f"La dependencia '{grupo.nombre}' pertenece a otro sector"
            )
    if _area_duplicada(db, nombre, dto.grupo_padre_id, dto.grupo_id):
        raise bad_request(f"Ya existe el área '{nombre}' en ese lugar")
    codigo = (
        _verificar_codigo(db, Area, dto.codigo)
        if dto.codigo
        else _codigo_libre(db, Area, nombre)
    )
    area = Area(
        nombre=nombre,
        codigo=codigo,
        grupo_padre_id=dto.grupo_padre_id,
        grupo_id=dto.grupo_id,
        activo=dto.activo,
    )
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.put("/areas/{area_id}", response_model=AreaOut)
def editar_area(area_id: int, dto: AreaUpd, db: DbSession, user: CurrentUser):
    _exigir_jefe(user)
    area = db.get(Area, area_id)
    if area is None:
        raise not_found("Área no encontrada")

    nuevo_padre = area.grupo_padre_id
    nuevo_grupo = area.grupo_id
    if "grupo_padre_id" in dto.model_fields_set and dto.grupo_padre_id is not None:
        if db.get(GrupoPadre, dto.grupo_padre_id) is None:
            raise bad_request(f"El sector {dto.grupo_padre_id} no existe")
        nuevo_padre = dto.grupo_padre_id
    if "grupo_id" in dto.model_fields_set:
        nuevo_grupo = dto.grupo_id
    if nuevo_grupo is not None:
        grupo = db.get(Grupo, nuevo_grupo)
        if grupo is None:
            raise bad_request(f"La dependencia {nuevo_grupo} no existe")
        nuevo_padre = grupo.grupo_padre_id

    if dto.nombre is not None:
        nombre = _texto(dto.nombre, "El nombre")
        if _area_duplicada(db, nombre, nuevo_padre, nuevo_grupo, area_id):
            raise bad_request(f"Ya existe el área '{nombre}' en ese lugar")
        area.nombre = nombre
    if dto.codigo is not None:
        area.codigo = _verificar_codigo(db, Area, dto.codigo, area_id)
    if dto.activo is not None:
        area.activo = dto.activo

    movido = (nuevo_padre, nuevo_grupo) != (area.grupo_padre_id, area.grupo_id)
    area.grupo_padre_id = nuevo_padre
    area.grupo_id = nuevo_grupo
    if movido:
        _propagar_area(db, area)
    if dto.actualizar_texto_legado:
        for atencion in db.scalars(
            select(Atencion).where(Atencion.area_id == area.id)
        ).all():
            atencion.area_solicitante = area.nombre
    db.commit()
    db.refresh(area)
    return area


@router.delete("/areas/{area_id}", status_code=204)
def borrar_area(area_id: int, db: DbSession, user: CurrentUser) -> None:
    _exigir_jefe(user)
    area = db.get(Area, area_id)
    if area is None:
        raise not_found("Área no encontrada")
    atenciones = _atenciones_area(db, area_id)
    if atenciones:
        raise bad_request(
            f"'{area.nombre}' tiene {atenciones} atenciones: no se puede borrar. "
            "Desactivala si ya no se usa."
        )
    db.delete(area)
    db.commit()


@router.post(
    "/areas/{area_id}/convertir-dependencia", response_model=AreaConversionOut
)
def convertir_area_en_dependencia(
    area_id: int, db: DbSession, user: CurrentUser
) -> dict[str, int | bool]:
    """Convierte un área en una dependencia nueva del mismo sector.

    Las atenciones pasan a colgar de la dependencia y el área vieja se elimina si
    queda sin atenciones; si no, se desactiva (el área no tiene jerarquía propia).
    """
    _exigir_jefe(user)
    area = db.get(Area, area_id)
    if area is None:
        raise not_found("Área no encontrada")
    if not area.activo:
        raise bad_request("El área está inactiva")
    repetida = db.scalars(
        select(Grupo).where(
            Grupo.nombre == area.nombre, Grupo.grupo_padre_id == area.grupo_padre_id
        )
    ).first()
    if repetida:
        raise bad_request(f"Ya existe una dependencia '{area.nombre}' en ese sector")
    grupo = Grupo(
        nombre=area.nombre,
        codigo=_codigo_libre(db, Grupo, area.codigo),
        grupo_padre_id=area.grupo_padre_id,
        activo=True,
    )
    db.add(grupo)
    db.flush()
    atenciones = db.scalars(
        select(Atencion).where(Atencion.area_id == area.id)
    ).all()
    for atencion in atenciones:
        atencion.area_id = None
        atencion.grupo_id = grupo.id
    db.flush()
    if _atenciones_area(db, area.id):
        area.activo = False
        eliminada = False
    else:
        db.delete(area)
        eliminada = True
    db.commit()
    db.refresh(grupo)
    return {
        "grupo_id": grupo.id,
        "atenciones_movidas": len(atenciones),
        "area_eliminada": eliminada,
    }
