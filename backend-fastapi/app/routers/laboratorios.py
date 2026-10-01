"""Laboratorios service (Fase 2): labs, categorias and lab atenciones."""

import calendar
import csv
import io
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import extract, func, select

from app.core.errors import bad_request, conflict, forbidden, not_found, unauthorized
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.horario import Horario
from app.models.laboratorio import LabAtencion, LabCategoria, Laboratorio
from app.models.usuario import Usuario
from app.schemas.atencion import PorCategoria, PorMes
from app.schemas.laboratorio import (
    LabAtencionCreate,
    LabAtencionOut,
    LabAtencionUpdate,
    LabCategoriaCreate,
    LabCategoriaOut,
    LabCategoriaUpdate,
    LaboratorioCreate,
    LaboratorioOut,
    LaboratorioUpdate,
    LabStatsOut,
    PorLab,
)
from app.services.horarios import esta_fuera_de_horario
from app.services.lab_categorias import (
    buscar_categoria,
    get_categorias_activas,
    validar_categoria,
)

router = APIRouter(prefix="/api/laboratorios", tags=["laboratorios"])

CSV_HEADER = (
    "id,laboratorio,categoria,auxiliar,descripcion,fecha_registro,fuera_de_turno"
)


def _solo_jefe(user: Usuario) -> None:
    if not is_privileged(user):
        raise forbidden("Solo un jefe puede gestionar laboratorios")


def _horario_del_mes(db: DbSession, usuario_id: int) -> Horario | None:
    now = datetime.now(UTC)
    return db.scalars(
        select(Horario).where(
            Horario.usuario_id == usuario_id,
            Horario.mes == now.month,
            Horario.anio == now.year,
        )
    ).first()


def _fuera_de_turno(db: DbSession, user: Usuario) -> bool:
    horario = _horario_del_mes(db, user.id)
    if horario is None:
        return False
    return esta_fuera_de_horario(
        horario.hora_inicio1,
        horario.hora_fin1,
        horario.hora_inicio2,
        horario.hora_fin2,
        datetime.now(UTC),
    )


def _serializar(db: DbSession, rows: list[LabAtencion]) -> list[dict[str, object]]:
    uids = {r.usuario_id for r in rows}
    nombres_u = {
        u.id: u.display_name
        for u in db.scalars(select(Usuario).where(Usuario.id.in_(uids or [-1]))).all()
    }
    lids = {r.laboratorio_id for r in rows}
    nombres_l = {
        lab.id: lab.nombre
        for lab in db.scalars(
            select(Laboratorio).where(Laboratorio.id.in_(lids or [-1]))
        ).all()
    }
    cids = {r.categoria_id for r in rows}
    nombres_c = {
        c.id: c.nombre
        for c in db.scalars(
            select(LabCategoria).where(LabCategoria.id.in_(cids or [-1]))
        ).all()
    }
    return [
        {
            "id": r.id,
            "usuario_id": r.usuario_id,
            "usuario_nombre": nombres_u.get(r.usuario_id, ""),
            "laboratorio_id": r.laboratorio_id,
            "laboratorio": nombres_l.get(r.laboratorio_id, ""),
            "categoria_id": r.categoria_id,
            "categoria": nombres_c.get(r.categoria_id, ""),
            "auxiliar_nombre": r.auxiliar_nombre,
            "descripcion": r.descripcion,
            "solucion": r.solucion,
            "observaciones": r.observaciones,
            "fuera_de_turno": r.fuera_de_turno,
            "fecha_registro": r.fecha_registro,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def _parse_ym(value: str | None, campo: str) -> tuple[int, int] | None:
    if value is None:
        return None
    try:
        anio_s, mes_s = value.split("-")
        anio, mes = int(anio_s), int(mes_s)
        if not 1 <= mes <= 12:
            raise ValueError
        return anio, mes
    except ValueError:
        raise bad_request(f"{campo} debe ser YYYY-MM") from None


def _filtros(
    laboratorio_id: int | None, desde_ym: str | None, hasta_ym: str | None
) -> list[Any]:
    filtros: list[Any] = []
    if laboratorio_id is not None:
        filtros.append(LabAtencion.laboratorio_id == laboratorio_id)
    desde = _parse_ym(desde_ym, "desde_ym")
    if desde is not None:
        filtros.append(LabAtencion.fecha_registro >= date(desde[0], desde[1], 1))
    hasta = _parse_ym(hasta_ym, "hasta_ym")
    if hasta is not None:
        ultimo = calendar.monthrange(hasta[0], hasta[1])[1]
        filtros.append(LabAtencion.fecha_registro <= date(hasta[0], hasta[1], ultimo))
    return filtros


@router.get("/cards")
def get_cards(db: DbSession, user: CurrentUser) -> dict[str, list[LaboratorioOut]]:
    labs = db.scalars(select(Laboratorio).order_by(Laboratorio.codigo)).all()
    return {
        "activas": [LaboratorioOut.model_validate(lab) for lab in labs if lab.activa],
        "inactivas": [
            LaboratorioOut.model_validate(lab) for lab in labs if not lab.activa
        ],
    }


@router.post("/", response_model=LaboratorioOut)
def create_lab(dto: LaboratorioCreate, db: DbSession, user: CurrentUser):
    _solo_jefe(user)
    codigo = dto.codigo.strip()
    nombre = dto.nombre.strip()
    if not codigo or not nombre:
        raise bad_request("Codigo y nombre son obligatorios")
    if db.scalar(select(Laboratorio).where(Laboratorio.codigo == codigo)) is not None:
        raise bad_request(f"Laboratorio con codigo '{codigo}' ya existe")
    lab = Laboratorio(codigo=codigo, nombre=nombre, activa=True,
                      created_at=datetime.now(UTC))
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


@router.put("/{lab_id}", status_code=204)
def update_lab(lab_id: int, dto: LaboratorioUpdate, db: DbSession, user: CurrentUser):
    _solo_jefe(user)
    lab = db.get(Laboratorio, lab_id)
    if lab is None:
        raise not_found("Laboratorio no encontrado")
    if dto.codigo is not None:
        codigo = dto.codigo.strip()
        if not codigo:
            raise bad_request("Codigo no puede estar vacio")
        otro = db.scalar(select(Laboratorio).where(Laboratorio.codigo == codigo))
        if otro is not None and otro.id != lab.id:
            raise bad_request(f"Laboratorio con codigo '{codigo}' ya existe")
        lab.codigo = codigo
    if dto.nombre is not None:
        if not dto.nombre.strip():
            raise bad_request("Nombre no puede estar vacio")
        lab.nombre = dto.nombre.strip()
    if dto.activa is not None:
        lab.activa = dto.activa
    db.commit()


@router.get("/categorias", response_model=list[LabCategoriaOut])
def get_categorias(
    db: DbSession, user: CurrentUser, todas: bool = Query(default=False)
):
    if todas and not is_privileged(user):
        raise forbidden("Solo un jefe puede ver todas las categorias")
    if todas:
        rows = db.scalars(select(LabCategoria).order_by(LabCategoria.nombre)).all()
        return list(rows)
    return get_categorias_activas(db)


@router.post("/categorias", response_model=LabCategoriaOut)
def create_categoria(dto: LabCategoriaCreate, db: DbSession, user: CurrentUser):
    _solo_jefe(user)
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre es obligatorio")
    if buscar_categoria(db, nombre) is not None:
        raise bad_request(f"Categoria '{nombre}' ya existe")
    cat = LabCategoria(nombre=nombre, activa=True, created_at=datetime.now(UTC))
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/categorias/{cat_id}", status_code=204)
def update_categoria(
    cat_id: int, dto: LabCategoriaUpdate, db: DbSession, user: CurrentUser
):
    _solo_jefe(user)
    cat = db.get(LabCategoria, cat_id)
    if cat is None:
        raise not_found("Categoria no encontrada")
    if dto.nombre is not None:
        nombre = dto.nombre.strip()
        if not nombre:
            raise bad_request("Nombre no puede estar vacio")
        otra = buscar_categoria(db, nombre)
        if otra is not None and otra.id != cat.id:
            raise bad_request(f"Categoria '{nombre}' ya existe")
        cat.nombre = nombre
    if dto.activa is not None:
        cat.activa = dto.activa
    db.commit()


@router.post("/atenciones", response_model=LabAtencionOut)
def create_lab_atencion(dto: LabAtencionCreate, db: DbSession, user: CurrentUser):
    lab = db.get(Laboratorio, dto.laboratorio_id)
    if lab is None:
        raise not_found("Laboratorio no encontrado")
    if not lab.activa:
        raise HTTPException(status_code=422, detail="Laboratorio inactivo")
    cat = validar_categoria(db, dto.categoria)
    descripcion = dto.descripcion.strip()
    solucion = dto.solucion.strip()
    if not descripcion or not solucion:
        raise bad_request("Descripcion y solucion son obligatorias")
    now = datetime.now(UTC)
    dup = db.scalar(
        select(LabAtencion).where(
            LabAtencion.usuario_id == user.id,
            LabAtencion.laboratorio_id == lab.id,
            LabAtencion.categoria_id == cat.id,
            LabAtencion.descripcion == descripcion,
            LabAtencion.created_at >= now - timedelta(seconds=60),
        )
    )
    if dup is not None:
        raise conflict("Atencion duplicada en los ultimos 60 segundos")
    row = LabAtencion(
        usuario_id=user.id,
        laboratorio_id=lab.id,
        categoria_id=cat.id,
        auxiliar_nombre=dto.auxiliar_nombre.strip() or user.display_name,
        descripcion=descripcion,
        solucion=solucion,
        observaciones=dto.observaciones,
        fuera_de_turno=_fuera_de_turno(db, user),
        fecha_registro=dto.fecha_registro or now.date(),
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serializar(db, [row])[0]


@router.get("/atenciones", response_model=list[LabAtencionOut])
def get_lab_atenciones(db: DbSession, user: CurrentUser, usuario_id: int | None = None):
    q = select(LabAtencion)
    if is_privileged(user):
        if usuario_id is not None:
            q = q.where(LabAtencion.usuario_id == usuario_id)
    else:
        q = q.where(LabAtencion.usuario_id == user.id)
    rows = db.scalars(
        q.order_by(LabAtencion.fecha_registro.desc(), LabAtencion.id.desc())
    ).all()
    return _serializar(db, list(rows))


def _dueño_o_jefe(row: LabAtencion, user: Usuario) -> None:
    if row.usuario_id != user.id and not is_privileged(user):
        raise forbidden("Solo el dueño o un jefe puede modificar la atencion")


@router.put("/atenciones/{atencion_id}", status_code=204)
def update_lab_atencion(
    atencion_id: int, dto: LabAtencionUpdate, db: DbSession, user: CurrentUser
):
    row = db.get(LabAtencion, atencion_id)
    if row is None:
        raise not_found("Atencion no encontrada")
    _dueño_o_jefe(row, user)
    if dto.laboratorio_id is not None:
        lab = db.get(Laboratorio, dto.laboratorio_id)
        if lab is None:
            raise not_found("Laboratorio no encontrado")
        if not lab.activa:
            raise HTTPException(status_code=422, detail="Laboratorio inactivo")
        row.laboratorio_id = lab.id
    if dto.categoria is not None:
        row.categoria_id = validar_categoria(db, dto.categoria).id
    if dto.auxiliar_nombre is not None:
        row.auxiliar_nombre = dto.auxiliar_nombre.strip()
    if dto.descripcion is not None:
        if not dto.descripcion.strip():
            raise bad_request("Descripcion no puede estar vacia")
        row.descripcion = dto.descripcion.strip()
    if dto.solucion is not None:
        if not dto.solucion.strip():
            raise bad_request("Solucion no puede estar vacia")
        row.solucion = dto.solucion.strip()
    if dto.observaciones is not None:
        row.observaciones = dto.observaciones
    if dto.fecha_registro is not None:
        row.fecha_registro = dto.fecha_registro
    db.commit()


@router.delete("/atenciones/{atencion_id}", status_code=204)
def delete_lab_atencion(atencion_id: int, db: DbSession, user: CurrentUser):
    row = db.get(LabAtencion, atencion_id)
    if row is None:
        raise not_found("Atencion no encontrada")
    _dueño_o_jefe(row, user)
    db.delete(row)
    db.commit()


@router.get("/stats", response_model=LabStatsOut)
def get_lab_stats(
    db: DbSession,
    user: CurrentUser,
    laboratorio_id: int | None = None,
    desde_ym: str | None = None,
    hasta_ym: str | None = None,
):
    if not is_privileged(user):
        raise unauthorized("Sin permiso")
    f = _filtros(laboratorio_id, desde_ym, hasta_ym)
    total = db.scalar(select(func.count()).select_from(LabAtencion).where(*f)) or 0
    por_lab = [
        PorLab(laboratorio_id=r[0], laboratorio=r[1], total=r[2])
        for r in db.execute(
            select(Laboratorio.id, Laboratorio.nombre, func.count())
            .join(LabAtencion, LabAtencion.laboratorio_id == Laboratorio.id)
            .where(*f)
            .group_by(Laboratorio.id, Laboratorio.nombre)
            .order_by(func.count().desc())
        ).all()
    ]
    if total == 0 and laboratorio_id is not None:
        lab = db.get(Laboratorio, laboratorio_id)
        if lab is not None:
            por_lab = [PorLab(laboratorio_id=lab.id, laboratorio=lab.nombre, total=0)]
    por_categoria = [
        PorCategoria(categoria=r[0], total=r[1])
        for r in db.execute(
            select(LabCategoria.nombre, func.count())
            .join(LabAtencion, LabAtencion.categoria_id == LabCategoria.id)
            .where(*f)
            .group_by(LabCategoria.nombre)
            .order_by(func.count().desc())
        ).all()
    ]
    por_mes = [
        PorMes(anio=int(r[0]), mes=int(r[1]), total=r[2])
        for r in db.execute(
            select(
                extract("year", LabAtencion.fecha_registro),
                extract("month", LabAtencion.fecha_registro),
                func.count(),
            )
            .where(*f)
            .group_by(
                extract("year", LabAtencion.fecha_registro),
                extract("month", LabAtencion.fecha_registro),
            )
            .order_by(
                extract("year", LabAtencion.fecha_registro),
                extract("month", LabAtencion.fecha_registro),
            )
        ).all()
    ]
    return LabStatsOut(
        total=total, por_lab=por_lab, por_categoria=por_categoria, por_mes=por_mes
    )


@router.get("/export.csv")
def export_lab_csv(
    db: DbSession,
    user: CurrentUser,
    laboratorio_id: int | None = None,
    desde_ym: str | None = None,
    hasta_ym: str | None = None,
):
    if not is_privileged(user):
        raise unauthorized("Sin permiso")
    f = _filtros(laboratorio_id, desde_ym, hasta_ym)
    rows = db.scalars(
        select(LabAtencion)
        .where(*f)
        .order_by(LabAtencion.fecha_registro.desc(), LabAtencion.id.desc())
    ).all()
    serial = _serializar(db, list(rows))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_HEADER.split(","))
    for r in serial:
        w.writerow(
            [
                r["id"],
                r["laboratorio"],
                r["categoria"],
                r["auxiliar_nombre"],
                r["descripcion"],
                r["fecha_registro"],
                str(bool(r["fuera_de_turno"])).lower(),
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lab_atenciones.csv"},
    )
