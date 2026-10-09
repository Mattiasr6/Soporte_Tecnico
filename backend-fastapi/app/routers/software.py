"""Software, plantillas y estados por PC (seguimiento de programas)."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import delete, select

from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.lab_pc import LabPc
from app.models.laboratorio import LabAtencion, LabCategoria, Laboratorio
from app.models.software import LabPlantilla, PcSoftware, Software, SoftwareLab
from app.models.usuario import Usuario  # noqa: F401  (registra el modelo)
from app.routers.laboratorios import (
    TURNOS,
    _equipo,
    _gestiona_equipo,
    _norm_nb,
    _serializar,
    nombre_vinculado,
)
from app.schemas.software import (
    LabSoftwareIn,
    PcEstadoIn,
    PlantillaIn,
    SoftwareIn,
)
from app.services.auditoria import diff, registrar
from app.services.lab_categorias import validar_categoria

router = APIRouter(prefix="/api/software", tags=["software"])

ESTADOS_PC = ("instalado", "falta", "dañado")
ACCION_TEXTO = {
    "instalado": ("instalado en", "Instalación verificada en sala"),
    "falta": ("falta en", "Pendiente de instalación"),
    "dañado": ("dañado en", "Pendiente de revisión"),
}


def _software_out(db: DbSession, sw: Software) -> dict[str, object]:
    labs = [
        r.laboratorio_id
        for r in db.scalars(
            select(SoftwareLab).where(SoftwareLab.software_id == sw.id)
        ).all()
    ]
    return {
        "id": sw.id,
        "nombre": sw.nombre,
        "licencia": sw.licencia,
        "uso": sw.uso,
        "esencial": sw.esencial,
        "docentes": sw.docentes,
        "activo": sw.activo,
        "labs": sorted(labs),
    }


@router.get("")
def listar(db: DbSession, user: CurrentUser) -> list[dict[str, object]]:
    del user
    sws = db.scalars(select(Software).order_by(Software.nombre)).all()
    return [_software_out(db, s) for s in sws]


@router.post("", status_code=201)
def crear(dto: SoftwareIn, db: DbSession, user: CurrentUser) -> dict[str, object]:
    _gestiona_equipo(user)
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre obligatorio")
    if db.scalar(select(Software).where(Software.nombre == nombre)) is not None:
        raise bad_request(f"Software '{nombre}' ya existe")
    sw = Software(
        nombre=nombre,
        licencia=dto.licencia.strip() or "gratuita",
        uso=dto.uso.strip(),
        esencial=dto.esencial,
        docentes=dto.docentes,
        activo=dto.activo,
        created_at=datetime.now(UTC),
    )
    db.add(sw)
    db.flush()
    registrar(db, user, "crear", "software", sw.id, f"{nombre} ({sw.licencia})")
    db.commit()
    db.refresh(sw)
    return _software_out(db, sw)


@router.put("/{software_id}")
def editar(
    software_id: int, dto: SoftwareIn, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    _gestiona_equipo(user)
    sw = db.get(Software, software_id)
    if sw is None:
        raise not_found("Software no encontrado")
    antes = {
        "nombre": sw.nombre,
        "licencia": sw.licencia,
        "uso": sw.uso,
        "esencial": sw.esencial,
        "docentes": sw.docentes,
        "activo": sw.activo,
    }
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre obligatorio")
    otro = db.scalar(select(Software).where(Software.nombre == nombre))
    if otro is not None and otro.id != sw.id:
        raise bad_request(f"Software '{nombre}' ya existe")
    sw.nombre = nombre
    sw.licencia = dto.licencia.strip() or "gratuita"
    sw.uso = dto.uso.strip()
    sw.esencial = dto.esencial
    sw.docentes = dto.docentes
    sw.activo = dto.activo
    cambios = diff(antes, {k: getattr(sw, k) for k in antes})
    if cambios:
        registrar(db, user, "editar", "software", software_id, cambios)
    db.commit()
    db.refresh(sw)
    return _software_out(db, sw)


@router.get("/esenciales")
def esenciales(db: DbSession, user: CurrentUser) -> list[dict[str, object]]:
    del user
    sws = (
        db.scalars(
            select(Software)
            .where(Software.esencial.is_(True), Software.activo.is_(True))
            .order_by(Software.nombre)
        ).all()
    )
    return [_software_out(db, s) for s in sws]


@router.get("/plantillas")
def listar_plantillas(db: DbSession, user: CurrentUser) -> list[dict[str, object]]:
    del user
    rows = db.scalars(select(LabPlantilla).order_by(LabPlantilla.nombre)).all()
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "descripcion": p.descripcion,
            "solucion": p.solucion,
            "turno": p.turno,
            "activa": p.activa,
        }
        for p in rows
    ]


@router.post("/plantillas", status_code=201)
def crear_plantilla(
    dto: PlantillaIn, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    _gestiona_equipo(user)
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre obligatorio")
    validar_categoria(db, dto.categoria)
    if dto.turno is not None and dto.turno not in TURNOS:
        raise bad_request(f"Turno debe ser uno de: {', '.join(TURNOS)}")
    p = LabPlantilla(
        nombre=nombre,
        categoria=dto.categoria.strip(),
        descripcion=dto.descripcion.strip(),
        solucion=dto.solucion.strip(),
        turno=dto.turno,
        activa=dto.activa,
        created_at=datetime.now(UTC),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "categoria": p.categoria,
        "descripcion": p.descripcion,
        "solucion": p.solucion,
        "turno": p.turno,
        "activa": p.activa,
    }


@router.put("/plantillas/{plantilla_id}")
def editar_plantilla(
    plantilla_id: int, dto: PlantillaIn, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    _gestiona_equipo(user)
    p = db.get(LabPlantilla, plantilla_id)
    if p is None:
        raise not_found("Plantilla no encontrada")
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre obligatorio")
    validar_categoria(db, dto.categoria)
    if dto.turno is not None and dto.turno not in TURNOS:
        raise bad_request(f"Turno debe ser uno de: {', '.join(TURNOS)}")
    p.nombre = nombre
    p.categoria = dto.categoria.strip()
    p.descripcion = dto.descripcion.strip()
    p.solucion = dto.solucion.strip()
    p.turno = dto.turno
    p.activa = dto.activa
    db.commit()
    db.refresh(p)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "categoria": p.categoria,
        "descripcion": p.descripcion,
        "solucion": p.solucion,
        "turno": p.turno,
        "activa": p.activa,
    }


@router.get("/laboratorios/{lab_id}")
def software_de_lab(
    lab_id: int, db: DbSession, user: CurrentUser
) -> list[dict[str, object]]:
    del user
    if db.get(Laboratorio, lab_id) is None:
        raise not_found("Laboratorio no encontrado")
    sws = (
        db.scalars(
            select(Software)
            .join(SoftwareLab, SoftwareLab.software_id == Software.id)
            .where(SoftwareLab.laboratorio_id == lab_id)
            .order_by(Software.nombre)
        ).all()
    )
    return [_software_out(db, s) for s in sws]


@router.put("/laboratorios/{lab_id}")
def definir_software_lab(
    lab_id: int, dto: LabSoftwareIn, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    _gestiona_equipo(user)
    if db.get(Laboratorio, lab_id) is None:
        raise not_found("Laboratorio no encontrado")
    for sw_id in dto.software_ids:
        if db.get(Software, sw_id) is None:
            raise bad_request(f"Software #{sw_id} no existe")
    previos = {
        r.software_id
        for r in db.scalars(
            select(SoftwareLab).where(SoftwareLab.laboratorio_id == lab_id)
        ).all()
    }
    nuevos = set(dict.fromkeys(dto.software_ids))
    quitados = sorted(previos - nuevos)
    agregados = sorted(nuevos - previos)
    if quitados or agregados:
        nombres = _nombres_de(db, set(quitados) | set(agregados))
        detalle = (
            f"programas {len(previos)} -> {len(nuevos)}; "
            f"quitados: {_lista(nombres, quitados)}; "
            f"agregados: {_lista(nombres, agregados)}"
        )
        registrar(db, user, "editar", "software_lab", lab_id, detalle)
    db.execute(delete(SoftwareLab).where(SoftwareLab.laboratorio_id == lab_id))
    for sw_id in nuevos:
        db.add(SoftwareLab(software_id=sw_id, laboratorio_id=lab_id, created_at=datetime.now(UTC)))
    db.commit()
    return {"actualizados": len(nuevos)}


def _nombres_de(db: DbSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {
        s.id: s.nombre
        for s in db.scalars(select(Software).where(Software.id.in_(ids))).all()
    }


def _lista(nombres: dict[int, str], ids: list[int]) -> str:
    return ", ".join(nombres.get(i, f"#{i}") for i in ids) or "-"


@router.get("/pcs/{pc_id}")
def estados_de_pc(
    pc_id: int, db: DbSession, user: CurrentUser
) -> list[dict[str, object]]:
    del user
    pc = db.get(LabPc, pc_id)
    if pc is None:
        raise not_found("PC no encontrada")
    estados = {
        r.software_id: r.estado
        for r in db.scalars(select(PcSoftware).where(PcSoftware.pc_id == pc_id)).all()
    }
    sws = (
        db.scalars(
            select(Software)
            .join(SoftwareLab, SoftwareLab.software_id == Software.id)
            .where(SoftwareLab.laboratorio_id == pc.laboratorio_id)
            .order_by(Software.nombre)
        ).all()
    )
    return [
        {"software_id": s.id, "nombre": s.nombre, "estado": estados.get(s.id, "falta")}
        for s in sws
    ]


@router.put("/pcs/{pc_id}")
def marcar_estado(
    pc_id: int, dto: PcEstadoIn, db: DbSession, user: CurrentUser
) -> dict[str, object]:
    pc = db.get(LabPc, pc_id)
    if pc is None:
        raise not_found("PC no encontrada")
    sw = db.get(Software, dto.software_id)
    if sw is None:
        raise bad_request("Software no existe")
    if dto.estado not in ESTADOS_PC:
        raise bad_request("estado debe ser instalado, falta o dañado")
    nombre_aux = (
        nombre_vinculado(user)
        or (dto.auxiliar_nombre or "").strip()
        or user.display_name
    )
    nomina = {_norm_nb(m["nombre"]) for m in _equipo()}
    if _norm_nb(nombre_aux) not in nomina:
        raise bad_request(f"Auxiliar '{nombre_aux}' no esta en la nomina")
    ahora = datetime.now(UTC)
    actual = db.scalar(
        select(PcSoftware).where(
            PcSoftware.pc_id == pc_id, PcSoftware.software_id == sw.id
        )
    )
    if actual is not None and actual.estado == dto.estado:
        return {"software_id": sw.id, "nombre": sw.nombre, "estado": actual.estado}
    if actual is None:
        actual = PcSoftware(
            pc_id=pc_id, software_id=sw.id, estado=dto.estado, created_at=ahora, updated_at=ahora
        )
        db.add(actual)
    else:
        actual.estado = dto.estado
        actual.updated_at = ahora
    verbo, solucion = ACCION_TEXTO[dto.estado]
    cat = validar_categoria(db, dto.categoria)
    lab = db.get(Laboratorio, pc.laboratorio_id)
    assert lab is not None
    atencion: Any = LabAtencion(
        usuario_id=user.id,
        laboratorio_id=lab.id,
        categoria_id=cat.id,
        auxiliar_nombre=nombre_aux,
        pc_nombre=pc.nombre,
        turno=None,
        medio_solicitud="Presencial",
        descripcion=f"{sw.nombre} {verbo} {pc.nombre}",
        solucion=solucion,
        observaciones=None,
        fuera_de_turno=False,
        fecha_registro=ahora.date(),
        created_at=ahora,
    )
    db.add(atencion)
    db.commit()
    return {
        "software_id": sw.id,
        "nombre": sw.nombre,
        "estado": dto.estado,
        "atencion_id": atencion.id,
    }


@router.get("/atenciones-pc/{pc_id}")
def atenciones_de_pc(
    pc_id: int, db: DbSession, user: CurrentUser
) -> list[dict[str, object]]:
    del user
    pc = db.get(LabPc, pc_id)
    if pc is None:
        raise not_found("PC no encontrada")
    rows = (
        db.scalars(
            select(LabAtencion)
            .where(LabAtencion.pc_nombre == pc.nombre)
            .order_by(LabAtencion.fecha_registro.desc(), LabAtencion.id.desc())
        ).all()
    )
    return _serializar(db, rows)


@router.get("/categorias-lab")
def categorias_lab(db: DbSession, user: CurrentUser) -> list[dict[str, object]]:
    del user
    rows = db.scalars(select(LabCategoria).order_by(LabCategoria.nombre)).all()
    return [{"id": c.id, "nombre": c.nombre} for c in rows]
