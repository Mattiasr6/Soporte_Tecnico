"""Paridad de AtencionesController .NET (S3). Identidad temporal X-User-Id (RN-S3-01)."""

import calendar
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import extract, func, select

from app.core.errors import bad_request, forbidden, not_found, unauthorized
from app.core.security import is_privileged, require_user
from app.db.session import DbSession
from app.models.area import Area
from app.models.atencion import Atencion
from app.models.grupo import Grupo
from app.models.grupo_padre import GrupoPadre
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.schemas.atencion import (
    AtencionBatchIn,
    AtencionBatchOut,
    AtencionCreate,
    AtencionOut,
    AtencionUpdate,
    PorArea,
    PorCategoria,
    PorMes,
    PorTecnico,
    StatsOut,
)
from app.services.categorias import CATEGORIAS_VALIDAS, normalizar_categoria
from app.services.csv_import import parse_csv
from app.services.horarios import esta_fuera_de_horario

router = APIRouter(prefix="/api/atenciones", tags=["atenciones"])

CurrentUser = Annotated[Usuario, Depends(require_user)]


def _nombres(
    db: DbSession, atenciones: list[Atencion]
) -> tuple[dict[int, str], dict[int, str], dict[int, str], dict[int, str]]:
    uids = {a.usuario_id for a in atenciones}
    uids |= {a.colaborador_id for a in atenciones if a.colaborador_id is not None}
    usuarios = (
        db.scalars(select(Usuario).where(Usuario.id.in_(uids))).all() if uids else []
    )
    nombres_u = {u.id: u.display_name for u in usuarios}
    gpids = {a.grupo_padre_id for a in atenciones if a.grupo_padre_id is not None}
    grupos_p = (
        db.scalars(select(GrupoPadre).where(GrupoPadre.id.in_(gpids))).all()
        if gpids
        else []
    )
    nombres_gp = {g.id: g.nombre for g in grupos_p}
    gids = {a.grupo_id for a in atenciones if a.grupo_id is not None}
    grupos = db.scalars(select(Grupo).where(Grupo.id.in_(gids))).all() if gids else []
    nombres_g = {g.id: g.nombre for g in grupos}
    aids = {a.area_id for a in atenciones if a.area_id is not None}
    areas = db.scalars(select(Area).where(Area.id.in_(aids))).all() if aids else []
    nombres_a = {a.id: a.nombre for a in areas}
    return nombres_u, nombres_gp, nombres_g, nombres_a


def _serializar(db: DbSession, atenciones: list[Atencion]) -> list[dict[str, object]]:
    nombres_u, nombres_gp, nombres_g, nombres_a = _nombres(db, atenciones)
    out = []
    for a in atenciones:
        colab = (
            nombres_u.get(a.colaborador_id) if a.colaborador_id is not None else None
        )
        out.append(
            {
                "id": a.id,
                "usuario_id": a.usuario_id,
                "usuario_nombre": nombres_u.get(a.usuario_id, ""),
                "area_solicitante": a.area_solicitante,
                "grupo_padre_id": a.grupo_padre_id,
                "grupo_padre_nombre": (
                    nombres_gp.get(a.grupo_padre_id)
                    if a.grupo_padre_id is not None
                    else None
                ),
                "grupo_id": a.grupo_id,
                "grupo_nombre": (
                    nombres_g.get(a.grupo_id) if a.grupo_id is not None else None
                ),
                "area_id": a.area_id,
                "area_nombre": (
                    nombres_a.get(a.area_id) if a.area_id is not None else None
                ),
                "medio_solicitud": a.medio_solicitud,
                "usuario_solicitante": a.usuario_solicitante,
                "categoria": a.categoria,
                "descripcion": a.descripcion,
                "solucion": a.solucion,
                "observaciones": a.observaciones,
                "enlace_apoyo": a.enlace_apoyo,
                "colaborador_id": a.colaborador_id,
                "colaborador_nombre": colab,
                "fecha_registro": a.fecha_registro,
                "fuera_de_turno": a.fuera_de_turno,
                "created_at": a.created_at,
            }
        )
    return out


def _horario_del_mes(db: DbSession, usuario_id: int) -> Horario | None:
    now = datetime.now(timezone.utc)
    return db.scalars(
        select(Horario).where(
            Horario.usuario_id == usuario_id,
            Horario.mes == now.month,
            Horario.anio == now.year,
        )
    ).first()


def _resolver_jerarquia(
    db: DbSession, item: AtencionCreate
) -> tuple[int | None, int | None, int | None, str]:
    gp_id = item.grupo_padre_id
    g_id = item.grupo_id
    ar_id = item.area_id
    legacy = item.area_solicitante.strip()
    if ar_id is not None:
        area = db.get(Area, ar_id)
        if area is None:
            raise bad_request(f"AreaId {ar_id} no existe")
        return area.grupo_padre_id, area.grupo_id, area.id, area.nombre
    if g_id is not None:
        grupo = db.get(Grupo, g_id)
        if grupo is None:
            raise bad_request(f"GrupoId {g_id} no existe")
        return grupo.grupo_padre_id, grupo.id, None, legacy or grupo.nombre
    if legacy:
        area = db.scalars(select(Area).where(Area.nombre == legacy)).first()
        if area is not None:
            return area.grupo_padre_id, area.grupo_id, area.id, legacy
        grupo = db.scalars(select(Grupo).where(Grupo.nombre == legacy)).first()
        if grupo is not None:
            return grupo.grupo_padre_id, grupo.id, None, legacy
        gp = db.scalars(select(GrupoPadre).where(GrupoPadre.nombre == legacy)).first()
        if gp is not None:
            return gp.id, None, None, legacy
    if gp_id is None and not legacy:
        raise bad_request(
            "Debe enviar area_solicitante o grupo_padre_id/grupo_id/area_id"
        )
    if not legacy and gp_id is not None:
        gp = db.get(GrupoPadre, gp_id)
        legacy = gp.nombre if gp is not None else "Desconocido"
    return gp_id, g_id, ar_id, legacy


@router.get("", response_model=list[AtencionOut])
def get_all(db: DbSession, user: CurrentUser, usuario_id: int | None = None):
    q = select(Atencion)
    if (user.role == "Jefe" or user.can_view_dashboard) and usuario_id is not None:
        q = q.where(Atencion.usuario_id == usuario_id)
    elif user.role != "Jefe" and not user.can_view_dashboard:
        q = q.where(Atencion.usuario_id == user.id)
    rows = db.scalars(
        q.order_by(Atencion.fecha_registro.desc(), Atencion.id.desc())
    ).all()
    return _serializar(db, list(rows))


def _filtros(
    usuario_id: int | None,
    desde_dia: int | None,
    desde_mes: int | None,
    desde_anio: int | None,
    hasta_dia: int | None,
    hasta_mes: int | None,
    hasta_anio: int | None,
) -> list[Any]:
    filtros: list[Any] = []
    if usuario_id is not None:
        filtros.append(Atencion.usuario_id == usuario_id)
    if desde_anio is not None and desde_mes is not None:
        filtros.append(
            Atencion.fecha_registro >= date(desde_anio, desde_mes, desde_dia or 1)
        )
    if hasta_anio is not None and hasta_mes is not None:
        ultimo = calendar.monthrange(hasta_anio, hasta_mes)[1]
        filtros.append(
            Atencion.fecha_registro <= date(hasta_anio, hasta_mes, hasta_dia or ultimo)
        )
    return filtros


@router.get("/stats", response_model=StatsOut)
def get_stats(
    db: DbSession,
    user: CurrentUser,
    usuario_id: int | None = None,
    desde_dia: int | None = None,
    desde_mes: int | None = None,
    desde_anio: int | None = None,
    hasta_dia: int | None = None,
    hasta_mes: int | None = None,
    hasta_anio: int | None = None,
):
    if not is_privileged(user):
        raise unauthorized("Sin permiso")
    f = _filtros(
        usuario_id,
        desde_dia,
        desde_mes,
        desde_anio,
        hasta_dia,
        hasta_mes,
        hasta_anio,
    )
    total = db.scalar(select(func.count()).select_from(Atencion).where(*f)) or 0
    fuera = (
        db.scalar(
            select(func.count())
            .select_from(Atencion)
            .where(*f, Atencion.fuera_de_turno.is_(True))
        )
        or 0
    )
    por_tecnico_rows = db.execute(
        select(Atencion.usuario_id, func.count())
        .where(*f)
        .group_by(Atencion.usuario_id)
        .order_by(func.count().desc())
    ).all()
    nombres_u = {
        u.id: u.display_name
        for u in db.scalars(
            select(Usuario).where(
                Usuario.id.in_([r[0] for r in por_tecnico_rows] or [-1])
            )
        ).all()
    }
    por_tecnico = [
        PorTecnico(usuario_id=r[0], display_name=nombres_u.get(r[0], ""), total=r[1])
        for r in por_tecnico_rows
    ]
    por_categoria = [
        PorCategoria(categoria=r[0], total=r[1])
        for r in db.execute(
            select(Atencion.categoria, func.count())
            .where(*f)
            .group_by(Atencion.categoria)
            .order_by(func.count().desc())
        ).all()
    ]
    por_mes = [
        PorMes(anio=int(r[0]), mes=int(r[1]), total=r[2])
        for r in db.execute(
            select(
                extract("year", Atencion.fecha_registro),
                extract("month", Atencion.fecha_registro),
                func.count(),
            )
            .where(*f)
            .group_by(
                extract("year", Atencion.fecha_registro),
                extract("month", Atencion.fecha_registro),
            )
            .order_by(
                extract("year", Atencion.fecha_registro),
                extract("month", Atencion.fecha_registro),
            )
        ).all()
    ]
    por_area = [
        PorArea(area=r[0], total=r[1])
        for r in db.execute(
            select(Atencion.area_solicitante, func.count())
            .where(*f)
            .group_by(Atencion.area_solicitante)
            .order_by(func.count().desc())
        ).all()
    ]
    f_asis = _filtros(
        None, desde_dia, desde_mes, desde_anio, hasta_dia, hasta_mes, hasta_anio
    )
    if usuario_id is not None:
        f_asis.append(Atencion.colaborador_id == usuario_id)
    asis_rows = db.execute(
        select(Atencion.colaborador_id, func.count())
        .where(*f_asis, Atencion.colaborador_id.is_not(None))
        .group_by(Atencion.colaborador_id)
        .order_by(func.count().desc())
    ).all()
    nombres_c = {
        u.id: u.display_name
        for u in db.scalars(
            select(Usuario).where(
                Usuario.id.in_([r[0] for r in asis_rows if r[0] is not None] or [-1])
            )
        ).all()
    }
    asistencias = [
        PorTecnico(usuario_id=r[0], display_name=nombres_c.get(r[0], ""), total=r[1])
        for r in asis_rows
        if r[0] is not None
    ]
    return StatsOut(
        total=total,
        fuera_de_turno=fuera,
        por_tecnico=por_tecnico,
        por_categoria=por_categoria,
        por_mes=por_mes,
        por_area=por_area,
        asistencias=asistencias,
    )


@router.post("/batch", response_model=AtencionBatchOut)
def create_batch(dto: AtencionBatchIn, db: DbSession, user: CurrentUser):
    if not dto.atenciones:
        raise bad_request("La lista de atenciones está vacía.")
    invalidas = sorted(
        {normalizar_categoria(a.categoria) for a in dto.atenciones}
        - set(CATEGORIAS_VALIDAS)
    )
    if invalidas:
        raise bad_request(
            f"Categorías inválidas: {', '.join(invalidas)}. "
            f"Use: {', '.join(sorted(CATEGORIAS_VALIDAS))}"
        )
    horario = _horario_del_mes(db, user.id)
    now = datetime.now(timezone.utc)
    nuevas = []
    for a in dto.atenciones:
        gp_id, g_id, ar_id, legacy = _resolver_jerarquia(db, a)
        fuera = (
            esta_fuera_de_horario(
                horario.hora_inicio1,
                horario.hora_fin1,
                horario.hora_inicio2,
                horario.hora_fin2,
                now,
            )
            if horario is not None
            else False
        )
        nuevas.append(
            Atencion(
                usuario_id=user.id,
                area_solicitante=legacy,
                grupo_padre_id=gp_id,
                grupo_id=g_id,
                area_id=ar_id,
                medio_solicitud=a.medio_solicitud,
                usuario_solicitante=a.usuario_solicitante,
                categoria=normalizar_categoria(a.categoria),
                descripcion=a.descripcion,
                solucion=a.solucion,
                observaciones=a.observaciones,
                enlace_apoyo=a.enlace_apoyo,
                colaborador_id=a.colaborador_id,
                fecha_registro=a.fecha_registro or now.date(),
                fuera_de_turno=fuera,
                created_at=now,
            )
        )
    db.add_all(nuevas)
    db.commit()
    return AtencionBatchOut(registros_insertados=len(nuevas))


@router.put("/{atencion_id}", status_code=204)
def update_atencion(
    atencion_id: int, dto: AtencionUpdate, db: DbSession, user: CurrentUser
) -> None:
    a = db.get(Atencion, atencion_id)
    if a is None:
        raise not_found("Atención no encontrada")
    if a.usuario_id != user.id and user.role != "Jefe":
        raise forbidden("Solo el dueño o un Jefe puede editar")
    if dto.area_solicitante is not None:
        a.area_solicitante = dto.area_solicitante
    if dto.grupo_padre_id is not None:
        a.grupo_padre_id = dto.grupo_padre_id
    if dto.grupo_id is not None:
        a.grupo_id = dto.grupo_id
    if dto.area_id is not None:
        a.area_id = dto.area_id
    if dto.area_id is not None:
        area = db.get(Area, dto.area_id)
        if area is not None:
            a.area_solicitante = area.nombre
    elif dto.grupo_id is not None and dto.area_id is None:
        grupo = db.get(Grupo, dto.grupo_id)
        if grupo is not None and not dto.area_solicitante:
            a.area_solicitante = grupo.nombre
    elif (
        dto.grupo_padre_id is not None and dto.grupo_id is None and dto.area_id is None
    ):
        gp = db.get(GrupoPadre, dto.grupo_padre_id)
        if gp is not None and not dto.area_solicitante:
            a.area_solicitante = gp.nombre
    if dto.medio_solicitud is not None:
        a.medio_solicitud = dto.medio_solicitud
    if dto.usuario_solicitante is not None:
        a.usuario_solicitante = dto.usuario_solicitante
    if dto.categoria is not None:
        a.categoria = dto.categoria
    if dto.descripcion is not None:
        a.descripcion = dto.descripcion
    if dto.solucion is not None:
        a.solucion = dto.solucion
    if dto.observaciones is not None:
        a.observaciones = dto.observaciones
    if dto.enlace_apoyo is not None:
        a.enlace_apoyo = dto.enlace_apoyo
    db.commit()


@router.delete("/{atencion_id}", status_code=204)
def delete_atencion(atencion_id: int, db: DbSession, user: CurrentUser) -> None:
    a = db.get(Atencion, atencion_id)
    if a is None:
        raise not_found("Atención no encontrada")
    if a.usuario_id != user.id and user.role != "Jefe":
        raise forbidden("Solo el dueño o un Jefe puede eliminar")
    db.delete(a)
    db.commit()


@router.post("/import-csv")
def import_csv(
    db: DbSession, user: CurrentUser, file: Annotated[UploadFile, File(...)]
):
    nombre = file.filename or ""
    contenido = file.file.read()
    if not contenido:
        raise bad_request("Debes subir un archivo CSV.")
    if not nombre.lower().endswith(".csv"):
        raise bad_request("El archivo debe tener extensión .csv")
    filas, errores = parse_csv(contenido)
    if not filas:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No se encontraron registros válidos en el CSV.",
                "errores": errores,
            },
        )
    horario = _horario_del_mes(db, user.id)
    now = datetime.now(timezone.utc)
    nuevas = []
    for f in filas:
        gp_id, g_id, ar_id, _ = _resolver_jerarquia(
            db,
            AtencionCreate(
                area_solicitante=f.area,
                medio_solicitud=f.medio,
                usuario_solicitante=f.usuario_solicitante,
                categoria=f.categoria,
                descripcion=f.descripcion,
                solucion=f.solucion,
            ),
        )
        fuera = (
            esta_fuera_de_horario(
                horario.hora_inicio1,
                horario.hora_fin1,
                horario.hora_inicio2,
                horario.hora_fin2,
                now,
            )
            if horario is not None
            else False
        )
        nuevas.append(
            Atencion(
                usuario_id=user.id,
                area_solicitante=f.area,
                grupo_padre_id=gp_id,
                grupo_id=g_id,
                area_id=ar_id,
                medio_solicitud=f.medio,
                usuario_solicitante=f.usuario_solicitante,
                categoria=f.categoria,
                descripcion=f.descripcion,
                solucion=f.solucion,
                observaciones=f.observaciones,
                enlace_apoyo=f.enlace,
                fecha_registro=f.fecha,
                fuera_de_turno=fuera,
                created_at=now,
            )
        )
    db.add_all(nuevas)
    db.commit()
    return {"registros_insertados": len(nuevas), "errores": errores or None}
