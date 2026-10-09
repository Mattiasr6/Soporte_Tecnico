"""Laboratorios service (Fase 2): labs, categorias and lab atenciones."""

import calendar
import csv
import io
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import Integer, extract, func, select

from app.core.errors import bad_request, conflict, forbidden, not_found, unauthorized
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.horario import Horario
from app.models.lab_pc import LabPc
from app.models.laboratorio import LabAtencion, LabCategoria, Laboratorio
from app.models.usuario import Usuario
from app.schemas.atencion import PorCategoria, PorMes
from app.schemas.laboratorio import (
    AuxiliarCreate,
    AuxiliarEntry,
    EncargadoIn,
    EquipoOut,
    EquipoReplace,
    LabAtencionCreate,
    LabAtencionOut,
    LabAtencionUpdate,
    LabCategoriaCreate,
    LabCategoriaOut,
    LabCategoriaUpdate,
    LaboratorioCreate,
    LaboratorioOut,
    LaboratorioUpdate,
    LabPcsIn,
    LabStatsOut,
    MiembroYoOut,
    PorAuxiliarFuera,
    PorLab,
    PorTurno,
    PorTurnoFuera,
    TurnoHorario,
    VinculoIn,
)
from app.services.auditoria import diff, registrar
from app.services.horarios import esta_fuera_de_horario
from app.services.lab_categorias import (
    buscar_categoria,
    get_categorias_activas,
    validar_categoria,
)

router = APIRouter(prefix="/api/laboratorios", tags=["laboratorios"])

CSV_HEADER = "id,laboratorio,categoria,auxiliar,turno,medio,descripcion,fecha_registro,fuera_de_turno"


def _solo_jefe(user: Usuario) -> None:
    if not is_privileged(user):
        raise forbidden("Solo un jefe puede gestionar laboratorios")


def _lectura_amplia(user: Usuario) -> bool:
    """Jefe o Encargado: lectura de equipo completo, sin escritura."""
    return is_privileged(user) or user.role == "Encargado"


def _gestiona_equipo(user: Usuario) -> None:
    """Jefe o Encargado: nómina y horarios. El resto sigue siendo de Jefe."""
    if not is_privileged(user) and user.role != "Encargado":
        raise forbidden("Solo Jefe o Encargado puede gestionar el equipo")


def _horario_del_mes(db: DbSession, usuario_id: int) -> Horario | None:
    now = datetime.now(UTC)
    return db.scalars(
        select(Horario).where(
            Horario.usuario_id == usuario_id,
            Horario.mes == now.month,
            Horario.anio == now.year,
        )
    ).first()


def _norm_nb(s: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFD", s.strip().casefold())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _fuera_de_turno_lab(auxiliar_nombre: str, turno: str | None) -> bool:
    """Fuera de turno por pertenencia, no por hora: el nombre no está en el turno."""
    if not turno or not (auxiliar_nombre or "").strip():
        return False
    try:
        bloque = _horarios().get(turno, {})
        miembros = bloque.get("auxiliares", []) if isinstance(bloque, dict) else []
    except Exception:  # noqa: BLE001 - fuera de turno es fail-closed
        return False
    return _norm_nb(auxiliar_nombre) not in {_norm_nb(str(n)) for n in miembros}


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
            "pc_nombre": r.pc_nombre,
            "turno": r.turno,
            "medio_solicitud": r.medio_solicitud or "Presencial",
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
    laboratorio_id: int | None,
    desde_ym: str | None,
    hasta_ym: str | None,
    turno: str | None = None,
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
    if turno is not None:
        if turno not in TURNOS:
            raise bad_request(f"Turno debe ser uno de: {', '.join(TURNOS)}")
        filtros.append(LabAtencion.turno == turno)
    return filtros


TURNOS: tuple[str, ...] = ("mañana", "mediodia", "tarde", "noche")

MEDIOS: tuple[str, ...] = ("Presencial", "WhatsApp")

_HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_EQUIPO_FILE = _DATA_DIR / "equipo_auxiliares.json"
_HORARIOS_FILE = _DATA_DIR / "horarios_auxiliares.json"


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
    return data if isinstance(data, dict) else default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _equipo() -> list[dict[str, Any]]:
    data = _read_json(_EQUIPO_FILE, {"auxiliares": []})
    raw = data.get("auxiliares")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict) and str(item.get("nombre", "")).strip():
            out.append(
                {
                    "nombre": str(item["nombre"]).strip(),
                    "activo": bool(item.get("activo", True)),
                    "encargado": bool(item.get("encargado", False)),
                    "usuario_id": _usuario_id_o_none(item.get("usuario_id")),
                }
            )
    return out


def _usuario_id_o_none(valor: object) -> int | None:
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None
    return valor


def _guardar_equipo(miembros: list[dict[str, Any]]) -> None:
    """Persiste la nómina; las entradas sin vínculo no ganan la clave usuario_id."""
    limpio = []
    for m in miembros:
        fila = {k: v for k, v in m.items() if k != "usuario_id"}
        if m.get("usuario_id") is not None:
            fila["usuario_id"] = m["usuario_id"]
        limpio.append(fila)
    _write_json(_EQUIPO_FILE, {"auxiliares": limpio})


ROLES_NOMINA: tuple[str, ...] = ("Auxiliar", "Encargado")
SIN_VINCULO = "Tu cuenta no está vinculada a la nómina; pedile al Jefe que la vincule"


def _miembro_de_cuenta(usuario_id: int) -> dict[str, Any] | None:
    return next((m for m in _equipo() if m["usuario_id"] == usuario_id), None)


def nombre_vinculado(user: Usuario) -> str | None:
    """Nombre de nómina con el que firma la cuenta.

    Auxiliar/Encargado firman siempre con el miembro vinculado a su cuenta (403 si no
    hay vínculo). Para Técnico/Jefe devuelve None: siguen eligiendo el nombre.
    """
    if user.role not in ROLES_NOMINA:
        return None
    miembro = _miembro_de_cuenta(user.id)
    if miembro is None:
        raise forbidden(SIN_VINCULO)
    return str(miembro["nombre"])


def _horarios() -> dict[str, dict[str, Any]]:
    data = _read_json(_HORARIOS_FILE, {})
    out = {}
    for turno in TURNOS:
        bloque = data.get(turno)
        if not isinstance(bloque, dict):
            continue
        aux = bloque.get("auxiliares")
        out[turno] = {
            "inicio": str(bloque.get("inicio", "")),
            "fin": str(bloque.get("fin", "")),
            "auxiliares": [str(n).strip() for n in aux if str(n).strip()]
            if isinstance(aux, list)
            else [],
        }
    return out


def _validar_turno(turno: str | None) -> str | None:
    if turno is None:
        return None
    if turno not in TURNOS:
        raise bad_request(f"Turno debe ser uno de: {', '.join(TURNOS)}")
    return turno


def _validar_medio(medio: str | None) -> str:
    if medio is None or not str(medio).strip():
        return "Presencial"
    if medio not in MEDIOS:
        raise bad_request(f"Medio debe ser uno de: {', '.join(MEDIOS)}")
    return medio


@router.get("/equipo", response_model=EquipoOut)
def get_equipo(db: DbSession, user: CurrentUser, turno: str | None = None) -> EquipoOut:
    del db, user
    miembros = _equipo()
    if turno is not None:
        _validar_turno(turno)
        en_turno = {n.lower() for n in _horarios().get(turno, {}).get("auxiliares", [])}
        miembros = [m for m in miembros if m["nombre"].lower() in en_turno]
    return EquipoOut(auxiliares=[AuxiliarEntry(**m) for m in miembros])


@router.post("/equipo", response_model=AuxiliarEntry)
def add_auxiliar(dto: AuxiliarCreate, db: DbSession, user: CurrentUser):
    _gestiona_equipo(user)
    del db
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre es obligatorio")
    miembros = _equipo()
    if any(m["nombre"].lower() == nombre.lower() for m in miembros):
        raise bad_request(f"Auxiliar '{nombre}' ya existe")
    miembros.append(
        {"nombre": nombre, "activo": True, "encargado": False, "usuario_id": None}
    )
    _guardar_equipo(miembros)
    return AuxiliarEntry(nombre=nombre, activo=True, encargado=False)


@router.put("/equipo", response_model=EquipoOut)
def replace_equipo(dto: EquipoReplace, db: DbSession, user: CurrentUser):
    _gestiona_equipo(user)
    del db
    # el vínculo con la cuenta solo lo cambia /equipo/vincular (Jefe): acá se conserva
    vinculos = {_norm_nb(m["nombre"]): m["usuario_id"] for m in _equipo()}
    vistos: set[str] = set()
    miembros = []
    for item in dto.auxiliares:
        nombre = item.nombre.strip()
        if not nombre:
            raise bad_request("Nombre no puede estar vacio")
        if nombre.lower() in vistos:
            raise bad_request(f"Auxiliar '{nombre}' duplicado")
        vistos.add(nombre.lower())
        miembros.append(
            {
                "nombre": nombre,
                "activo": item.activo,
                "encargado": item.encargado,
                "usuario_id": vinculos.get(_norm_nb(nombre)),
            }
        )
    _guardar_equipo(miembros)
    return EquipoOut(auxiliares=[AuxiliarEntry(**m) for m in miembros])


@router.post("/equipo/encargado", response_model=EquipoOut)
def set_encargado(dto: EncargadoIn, db: DbSession, user: CurrentUser):
    _gestiona_equipo(user)
    del db
    nombre = dto.nombre.strip()
    miembros = _equipo()
    for m in miembros:
        if m["nombre"].lower() == nombre.lower():
            m["encargado"] = dto.encargado
            break
    else:
        raise not_found(f"Auxiliar '{nombre}' no existe")
    _guardar_equipo(miembros)
    return EquipoOut(auxiliares=[AuxiliarEntry(**m) for m in miembros])


@router.post("/equipo/vincular", response_model=EquipoOut)
def vincular_cuenta(dto: VinculoIn, db: DbSession, user: CurrentUser):
    """Vincula (o desvincula con usuario_id null) un miembro de la nómina a una cuenta."""
    if not is_privileged(user):
        raise forbidden("Solo un jefe puede vincular cuentas a la nómina")
    miembros = _equipo()
    clave = _norm_nb(dto.nombre)
    miembro = next((m for m in miembros if _norm_nb(m["nombre"]) == clave), None)
    if miembro is None:
        raise not_found(f"Auxiliar '{dto.nombre.strip()}' no existe")
    if dto.usuario_id is not None:
        cuenta = db.get(Usuario, dto.usuario_id)
        if cuenta is None:
            raise not_found("Usuario no encontrado")
        if not cuenta.activo:
            raise bad_request("El usuario está desactivado")
        if cuenta.role not in ROLES_NOMINA:
            raise bad_request("Solo se vinculan cuentas Auxiliar o Encargado")
        for m in miembros:  # una cuenta, un miembro: revincular la mueve
            if m["usuario_id"] == dto.usuario_id:
                m["usuario_id"] = None
    miembro["usuario_id"] = dto.usuario_id
    _guardar_equipo(miembros)
    return EquipoOut(auxiliares=[AuxiliarEntry(**m) for m in miembros])


@router.get("/equipo/yo", response_model=MiembroYoOut)
def miembro_yo(db: DbSession, user: CurrentUser) -> MiembroYoOut:
    del db
    miembro = _miembro_de_cuenta(user.id)
    if miembro is None:
        raise not_found(SIN_VINCULO)
    return MiembroYoOut(
        nombre=miembro["nombre"],
        encargado=miembro["encargado"],
        activo=miembro["activo"],
    )


@router.get("/horarios")
def get_horarios(db: DbSession, user: CurrentUser) -> dict[str, dict[str, Any]]:
    del db, user
    return _horarios()


@router.get("/horarios/conteo")
def get_horarios_conteo(db: DbSession, user: CurrentUser) -> dict[str, int]:
    del db, user
    return {t: len(_horarios().get(t, {}).get("auxiliares", [])) for t in TURNOS}


@router.put("/horarios")
def put_horarios(
    payload: dict[str, TurnoHorario], db: DbSession, user: CurrentUser
) -> dict[str, dict[str, Any]]:
    _gestiona_equipo(user)
    del db
    if set(payload) != set(TURNOS):
        raise bad_request(f"Se esperan los turnos: {', '.join(TURNOS)}")
    import unicodedata

    def _norm(s: str) -> str:
        t = unicodedata.normalize("NFD", s.strip().casefold())
        return "".join(c for c in t if unicodedata.category(c) != "Mn")

    nomina = {_norm(m["nombre"]) for m in _equipo()}
    nuevo = {}
    for turno in TURNOS:
        bloque = payload[turno]
        if not _HORA_RE.match(bloque.inicio) or not _HORA_RE.match(bloque.fin):
            raise bad_request(f"Turno '{turno}': inicio/fin deben ser HH:MM")
        nombres = [n.strip() for n in bloque.auxiliares]
        if any(not n for n in nombres):
            raise bad_request(f"Turno '{turno}': nombre vacio")
        desconocidos = [n for n in nombres if _norm(n) not in nomina]
        if desconocidos:
            raise bad_request(
                f"Turno '{turno}': no estan en la nomina: {', '.join(desconocidos)}"
            )
        if len({_norm(n) for n in nombres}) != len(nombres):
            raise bad_request(f"Turno '{turno}': nombre duplicado")
        nuevo[turno] = {
            "inicio": bloque.inicio,
            "fin": bloque.fin,
            "auxiliares": nombres,
        }
    _write_json(_HORARIOS_FILE, nuevo)
    return nuevo


# ponytail: sábados por fecha, cupo 2/1/1-2 (el 5to cierra ambientes en tarde)
SABADO_TURNOS: tuple[str, ...] = ("mañana", "mediodia", "tarde")

SABADO_DEFAULTS: dict[str, dict[str, str]] = {
    "mañana": {"inicio": "08:00", "fin": "12:00"},
    "mediodia": {"inicio": "12:00", "fin": "16:00"},
    "tarde": {"inicio": "14:30", "fin": "18:30"},
}

SABADO_CUPO: dict[str, tuple[int, int]] = {
    "mañana": (2, 2),
    "mediodia": (1, 1),
    "tarde": (1, 2),
}

_SABADOS_FILE = _DATA_DIR / "horarios_sabados.json"
_FECHA_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _sabados() -> dict[str, dict[str, dict[str, Any]]]:
    data = _read_json(_SABADOS_FILE, {})
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for fecha, val in data.items():
        if not isinstance(val, dict):
            continue
        bloques: dict[str, dict[str, Any]] = {}
        for turno in SABADO_TURNOS:
            bloque = val.get(turno)
            if not isinstance(bloque, dict):
                continue
            aux = bloque.get("auxiliares")
            bloques[turno] = {
                "inicio": str(bloque.get("inicio", "")),
                "fin": str(bloque.get("fin", "")),
                "auxiliares": [str(n).strip() for n in aux if str(n).strip()]
                if isinstance(aux, list)
                else [],
            }
        out[str(fecha)] = bloques
    return out


def _validar_fecha_sabado(fecha: str) -> str:
    m = _FECHA_RE.match((fecha or "").strip())
    es_sabado = False
    if m:
        try:
            es_sabado = (
                date(int(m.group(1)), int(m.group(2)), int(m.group(3))).weekday()
                == 5
            )
        except ValueError:
            es_sabado = False
    if not es_sabado:
        raise bad_request("La fecha debe ser un sábado (YYYY-MM-DD)")
    assert m is not None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _sabados_del_mes(anio: int, mes: int) -> list[str]:
    if not 1 <= mes <= 12 or not 2000 <= anio <= 2100:
        raise bad_request("Mes debe ser 1-12 y año 2000-2100")
    _, ultimo = calendar.monthrange(anio, mes)
    return [
        date(anio, mes, d).isoformat()
        for d in range(1, ultimo + 1)
        if date(anio, mes, d).weekday() == 5
    ]


@router.get("/horarios-sabado")
def get_horarios_sabado(
    db: DbSession, user: CurrentUser, mes: int | None = None, anio: int | None = None
) -> dict[str, Any]:
    del db, user
    now = datetime.now(UTC)
    mes = now.month if mes is None else mes
    anio = now.year if anio is None else anio
    fechas = _sabados_del_mes(anio, mes)
    guardados = _sabados()
    conteo: dict[str, int] = {}
    sabados = []
    for f in fechas:
        bloques = guardados.get(f)
        sabados.append({"fecha": f, "bloques": bloques})
        if not bloques:
            continue
        vistos: set[str] = set()
        for turno in SABADO_TURNOS:
            for n in (bloques.get(turno) or {}).get("auxiliares", []):
                if n not in vistos:
                    vistos.add(n)
                    conteo[n] = conteo.get(n, 0) + 1
    return {"sabados": sabados, "conteo": conteo, "defaults": SABADO_DEFAULTS}


@router.put("/horarios-sabado/{fecha}")
def put_horario_sabado(
    fecha: str, payload: dict[str, TurnoHorario], db: DbSession, user: CurrentUser
) -> dict[str, dict[str, Any]]:
    _gestiona_equipo(user)
    del db
    import unicodedata

    fecha = _validar_fecha_sabado(fecha)
    if set(payload) != set(SABADO_TURNOS):
        raise bad_request(f"Se esperan los turnos: {', '.join(SABADO_TURNOS)}")

    def _norm(s: str) -> str:
        t = unicodedata.normalize("NFD", s.strip().casefold())
        return "".join(c for c in t if unicodedata.category(c) != "Mn")

    nomina = {_norm(m["nombre"]) for m in _equipo()}
    nuevo: dict[str, dict[str, Any]] = {}
    for turno in SABADO_TURNOS:
        bloque = payload[turno]
        if not _HORA_RE.match(bloque.inicio) or not _HORA_RE.match(bloque.fin):
            raise bad_request(f"Turno '{turno}': inicio/fin deben ser HH:MM")
        nombres = [n.strip() for n in bloque.auxiliares]
        if any(not n for n in nombres):
            raise bad_request(f"Turno '{turno}': nombre vacio")
        desconocidos = [n for n in nombres if _norm(n) not in nomina]
        if desconocidos:
            raise bad_request(
                f"Turno '{turno}': no estan en la nomina: {', '.join(desconocidos)}"
            )
        if len({_norm(n) for n in nombres}) != len(nombres):
            raise bad_request(f"Turno '{turno}': nombre duplicado")
        minimo, maximo = SABADO_CUPO[turno]
        if not minimo <= len(nombres) <= maximo:
            raise bad_request("Cupo sábado: mañana 2, mediodía 1, tarde 1-2")
        nuevo[turno] = {
            "inicio": bloque.inicio,
            "fin": bloque.fin,
            "auxiliares": nombres,
        }
    todos = [n for turno in SABADO_TURNOS for n in nuevo[turno]["auxiliares"]]
    if len({_norm(n) for n in todos}) != len(todos):
        raise bad_request("Un auxiliar no puede estar en dos turnos el mismo sábado")
    datos = _sabados()
    datos[fecha] = nuevo
    _write_json(_SABADOS_FILE, datos)
    return nuevo


@router.delete("/horarios-sabado/{fecha}", status_code=204)
def delete_horario_sabado(fecha: str, db: DbSession, user: CurrentUser) -> None:
    _gestiona_equipo(user)
    del db
    fecha = _validar_fecha_sabado(fecha)
    datos = _sabados()
    datos.pop(fecha, None)
    _write_json(_SABADOS_FILE, datos)


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
    _gestiona_equipo(user)
    codigo = dto.codigo.strip()
    nombre = dto.nombre.strip()
    if not codigo or not nombre:
        raise bad_request("Codigo y nombre son obligatorios")
    if db.scalar(select(Laboratorio).where(Laboratorio.codigo == codigo)) is not None:
        raise bad_request(f"Laboratorio con codigo '{codigo}' ya existe")
    lab = Laboratorio(
        codigo=codigo, nombre=nombre, activa=True, created_at=datetime.now(UTC)
    )
    db.add(lab)
    # flush para tener el Id antes de registrar el rastro
    db.flush()
    registrar(db, user, "crear", "laboratorio", lab.id, f"{codigo} ({nombre})")
    db.commit()
    db.refresh(lab)
    return lab


@router.put("/{lab_id}", status_code=204)
def update_lab(lab_id: int, dto: LaboratorioUpdate, db: DbSession, user: CurrentUser):
    _gestiona_equipo(user)
    lab = db.get(Laboratorio, lab_id)
    if lab is None:
        raise not_found("Laboratorio no encontrado")
    campos = (
        "codigo", "nombre", "activa", "procesador", "ram", "disco", "marca",
        "gpu", "monitores", "sillas", "capacidad", "pcs_estudiantes", "pcs_docentes",
    )
    antes = {c: getattr(lab, c) for c in campos}
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
    for campo in (
        "procesador", "ram", "disco", "marca", "gpu", "monitores",
        "sillas", "capacidad", "pcs_estudiantes", "pcs_docentes",
    ):
        valor = getattr(dto, campo)
        if valor is not None:
            setattr(lab, campo, valor if isinstance(valor, int) else str(valor).strip() or None)
    cambios = diff(antes, {c: getattr(lab, c) for c in campos})
    if cambios:
        registrar(db, user, "editar", "laboratorio", lab_id, cambios)
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
    _gestiona_equipo(user)
    nombre = dto.nombre.strip()
    if not nombre:
        raise bad_request("Nombre es obligatorio")
    if buscar_categoria(db, nombre) is not None:
        raise bad_request(f"Categoria '{nombre}' ya existe")
    cat = LabCategoria(
        nombre=nombre,
        descripcion=(dto.descripcion or "").strip() or None,
        activa=True,
        created_at=datetime.now(UTC),
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/categorias/{cat_id}", status_code=204)
def update_categoria(
    cat_id: int, dto: LabCategoriaUpdate, db: DbSession, user: CurrentUser
):
    _gestiona_equipo(user)
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
    if dto.descripcion is not None:
        cat.descripcion = dto.descripcion.strip() or None
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
    aux_nombre = dto.auxiliar_nombre.strip() or user.display_name
    nomina = {_norm_nb(m["nombre"]) for m in _equipo()}
    partes = [p.strip() for p in aux_nombre.split("+") if p.strip()] or [aux_nombre]
    propio = nombre_vinculado(user)
    if propio is not None:
        # el principal es siempre la cuenta; los extras siguen yendo por nombre
        extras = [p for p in partes[1:] if _norm_nb(p) != _norm_nb(propio)]
        partes = [propio, *extras]
        aux_nombre = " + ".join(partes)
    for p in partes:
        if _norm_nb(p) not in nomina:
            raise bad_request(f"Auxiliar '{p}' no esta en la nomina")
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
    if dup is not None and not dto.forzar_duplicado:
        raise conflict("Atencion duplicada en los ultimos 60 segundos")
    turno_val = _validar_turno(dto.turno)
    row = LabAtencion(
        usuario_id=user.id,
        laboratorio_id=lab.id,
        categoria_id=cat.id,
        auxiliar_nombre=aux_nombre,
        pc_nombre=(dto.pc_nombre or "").strip() or None,
        turno=turno_val,
        medio_solicitud=_validar_medio(dto.medio_solicitud),
        descripcion=descripcion,
        solucion=solucion,
        observaciones=dto.observaciones,
        fuera_de_turno=any(_fuera_de_turno_lab(p, turno_val) for p in partes),
        fecha_registro=dto.fecha_registro or now.date(),
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serializar(db, [row])[0]


@router.get("/atenciones", response_model=list[LabAtencionOut])
def get_lab_atenciones(
    db: DbSession,
    user: CurrentUser,
    usuario_id: int | None = None,
    laboratorio_id: int | None = None,
):
    q = select(LabAtencion)
    if _lectura_amplia(user):
        if usuario_id is not None:
            q = q.where(LabAtencion.usuario_id == usuario_id)
    else:
        q = q.where(LabAtencion.usuario_id == user.id)
    if laboratorio_id is not None:
        q = q.where(LabAtencion.laboratorio_id == laboratorio_id)
    rows = db.scalars(
        q.order_by(LabAtencion.fecha_registro.desc(), LabAtencion.id.desc())
    ).all()
    return _serializar(db, list(rows))


def _dueño_o_jefe(row: LabAtencion, user: Usuario) -> None:
    if row.usuario_id != user.id and not is_privileged(user):
        raise forbidden("Solo el dueño o un jefe puede modificar la atencion")


@router.get("/atenciones/{atencion_id}", response_model=LabAtencionOut)
def get_lab_atencion(atencion_id: int, db: DbSession, user: CurrentUser):
    row = db.get(LabAtencion, atencion_id)
    if row is None:
        raise not_found("Atencion no encontrada")
    if row.usuario_id != user.id and not _lectura_amplia(user):
        raise forbidden("Solo el dueño, un encargado o un jefe puede ver la atencion")
    return _serializar(db, [row])[0]


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
    if dto.turno is not None:
        row.turno = _validar_turno(dto.turno) if dto.turno else None
    if dto.medio_solicitud is not None:
        row.medio_solicitud = _validar_medio(dto.medio_solicitud)
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
    registrar(
        db,
        user,
        "eliminar",
        "atencion_lab",
        atencion_id,
        f"lab #{row.laboratorio_id}; PC {row.pc_nombre or '-'}; "
        f"{row.descripcion[:180]}",
    )
    db.delete(row)
    db.commit()


@router.get("/stats", response_model=LabStatsOut)
def get_lab_stats(
    db: DbSession,
    user: CurrentUser,
    laboratorio_id: int | None = None,
    desde_ym: str | None = None,
    hasta_ym: str | None = None,
    turno: str | None = None,
):
    if not _lectura_amplia(user):
        raise unauthorized("Sin permiso")
    f = _filtros(laboratorio_id, desde_ym, hasta_ym, turno)
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
    por_turno = [
        PorTurno(turno=r[0], total=r[1])
        for r in db.execute(
            select(LabAtencion.turno, func.count())
            .where(*f, LabAtencion.turno.is_not(None))
            .group_by(LabAtencion.turno)
            .order_by(func.count().desc())
        ).all()
    ]
    fuera_por_turno = [
        PorTurnoFuera(turno=r[0], total=r[1], fuera=r[2])
        for r in db.execute(
            select(
                LabAtencion.turno,
                func.count(),
                func.sum(func.cast(LabAtencion.fuera_de_turno, Integer)),
            )
            .where(*f, LabAtencion.turno.is_not(None))
            .group_by(LabAtencion.turno)
            .order_by(func.count().desc())
        ).all()
    ]
    fuera_por_auxiliar = [
        PorAuxiliarFuera(auxiliar=r[0] or "—", turno=r[1] or "—", fuera=r[2])
        for r in db.execute(
            select(
                LabAtencion.auxiliar_nombre,
                LabAtencion.turno,
                func.count(),
            )
            .where(*f, LabAtencion.fuera_de_turno.is_(True))
            .group_by(LabAtencion.auxiliar_nombre, LabAtencion.turno)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
    ]
    return LabStatsOut(
        total=total,
        por_lab=por_lab,
        por_categoria=por_categoria,
        por_mes=por_mes,
        por_turno=por_turno,
        fuera_por_turno=fuera_por_turno,
        fuera_por_auxiliar=fuera_por_auxiliar,
    )


@router.get("/export.csv")
def export_lab_csv(
    db: DbSession,
    user: CurrentUser,
    laboratorio_id: int | None = None,
    desde_ym: str | None = None,
    hasta_ym: str | None = None,
    turno: str | None = None,
):
    if not _lectura_amplia(user):
        raise unauthorized("Sin permiso")
    f = _filtros(laboratorio_id, desde_ym, hasta_ym, turno)
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
                r["turno"] or "",
                r["medio_solicitud"] or "Presencial",
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


XLSX_MEDIA = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ponytail: espeja sus Excel (nombres + fecha + turno), sin logo por ahora
TURNO_XLSX = {"mañana": "Mañana", "mediodia": "Medio Dia", "tarde": "Tarde", "noche": "Noche"}


def _libro_xlsx(
    titulo: str, cabecera: list[str], filas: list[list[object]], anchos: list[int]
) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    fino = Side(style="thin", color="9DB8AD")
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)
    n = len(cabecera)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
    titulo_celda = ws.cell(row=1, column=1, value=titulo)
    titulo_celda.font = Font(bold=True, size=14, color="1E3932")
    for i, h in enumerate(cabecera, start=1):
        c = ws.cell(row=2, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="006241")
        c.alignment = Alignment(horizontal="center")
        c.border = borde
    for f, fila in enumerate(filas, start=3):
        for i, valor in enumerate(fila, start=1):
            c = ws.cell(row=f, column=i, value=valor)
            c.border = borde
            if f % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F4F8F5")
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[ws.cell(row=2, column=i).column_letter].width = ancho
    ws.freeze_panes = "A3"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/horarios/export.xlsx")
def export_horarios_xlsx(
    db: DbSession,
    user: CurrentUser,
    tipo: str = "sabado",
    mes: int | None = None,
    anio: int | None = None,
) -> Response:
    del db, user
    titulo, cabecera, filas, nombre = _filas_export(tipo, mes, anio)
    anchos = [32, 14] + [12] * (len(cabecera) - 2)
    return Response(
        content=_libro_xlsx(titulo, cabecera, filas, anchos),
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename={nombre}.xlsx"},
    )


@router.get("/horarios/export.pdf")
def export_horarios_pdf(
    db: DbSession,
    user: CurrentUser,
    tipo: str = "sabado",
    mes: int | None = None,
    anio: int | None = None,
) -> Response:
    del db, user
    titulo, cabecera, filas, nombre = _filas_export(tipo, mes, anio)
    return Response(
        content=_hoja_pdf(titulo, cabecera, filas),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre}.pdf"},
    )


def _filas_export(
    tipo: str, mes: int | None, anio: int | None
) -> tuple[str, list[str], list[list[object]], str]:
    """Titulo, cabecera, filas y base del nombre de archivo para exportar."""
    import unicodedata

    def _norm(s: str) -> str:
        t = unicodedata.normalize("NFD", s.strip().casefold())
        return "".join(c for c in t if unicodedata.category(c) != "Mn")

    if tipo == "semanal":
        horarios = _horarios()
        filas: list[list[object]] = []
        for turno in TURNOS:
            b = horarios.get(turno, {})
            for nombre in b.get("auxiliares", []):
                filas.append(
                    [nombre, TURNO_XLSX[turno], b.get("inicio", ""), b.get("fin", "")]
                )
        return (
            "HORARIOS POR TURNO (SEMANAL)",
            ["NOMBRE", "TURNO", "INICIO", "FIN"],
            filas,
            "horarios_semanales",
        )
    if tipo != "sabado":
        raise bad_request("tipo debe ser semanal o sabado")
    now = datetime.now(UTC)
    mes = now.month if mes is None else mes
    anio = now.year if anio is None else anio
    fechas = _sabados_del_mes(anio, mes)
    guardados = _sabados()
    filas = []
    vistos: set[str] = set()
    for f in fechas:
        bloques = guardados.get(f) or {}
        for turno in SABADO_TURNOS:
            b = bloques.get(turno) or {}
            for nombre in b.get("auxiliares", []):
                vistos.add(_norm(str(nombre)))
                filas.append(
                    [nombre, f, TURNO_XLSX[turno], b.get("inicio", ""), b.get("fin", "")]
                )
    for m in _equipo():
        if m.get("activo", True) and _norm(m["nombre"]) not in vistos:
            filas.append([m["nombre"], "", "Libre", "", ""])
    return (
        f"HORARIOS TURNO SABADO {mes:02d}-{anio}",
        ["NOMBRE", "SABADO", "TURNO", "INICIO", "FIN"],
        filas,
        f"sabados_{anio}-{mes:02d}",
    )


def _hoja_pdf(titulo: str, cabecera: list[str], filas: list[list[object]]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30
    )
    partes = [Paragraph(titulo, getSampleStyleSheet()["Title"]), Spacer(1, 12)]
    datos = [cabecera] + [[str(v) for v in fila] for fila in filas]
    tabla = Table(datos, colWidths=[220, 90, 90, 70, 70][: len(cabecera)], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#006241")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9DB8AD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8F5")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    partes.append(tabla)
    doc.build(partes)
    return buf.getvalue()


# --- PCs por laboratorio (dibujo estilo sala de cine) ---

_MAX_DIM_PC = 30
_MAX_PCS = 200


def _pcs_de(db: DbSession, lab_id: int) -> list[LabPc]:
    return list(
        db.scalars(
            select(LabPc)
            .where(LabPc.laboratorio_id == lab_id)
            .order_by(LabPc.fila, LabPc.col, LabPc.id)
        ).all()
    )


@router.get("/{lab_id}/pcs")
def get_lab_pcs(lab_id: int, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    del user
    lab = db.get(Laboratorio, lab_id)
    if lab is None:
        raise not_found("Laboratorio no encontrado")
    return {
        "filas": lab.filas_pc,
        "cols": lab.cols_pc,
        "pcs": [
            {
                "id": pc.id,
                "nombre": pc.nombre,
                "fila": pc.fila,
                "col": pc.col,
                "activa": pc.activa,
            }
            for pc in _pcs_de(db, lab_id)
        ],
    }


@router.put("/{lab_id}/pcs")
def put_lab_pcs(
    lab_id: int, dto: LabPcsIn, db: DbSession, user: CurrentUser
) -> dict[str, Any]:
    _gestiona_equipo(user)
    lab = db.get(Laboratorio, lab_id)
    if lab is None:
        raise not_found("Laboratorio no encontrado")
    if not 0 <= dto.filas <= _MAX_DIM_PC or not 0 <= dto.cols <= _MAX_DIM_PC:
        raise bad_request(f"Filas/columnas deben estar entre 0 y {_MAX_DIM_PC}")
    if len(dto.pcs) > _MAX_PCS:
        raise bad_request(f"Maximo {_MAX_PCS} PCs por laboratorio")
    if dto.pcs and (dto.filas < 1 or dto.cols < 1):
        raise bad_request("La grilla necesita filas y columnas para tener PCs")
    import unicodedata

    def _norm(s: str) -> str:
        t = unicodedata.normalize("NFD", s.strip().casefold())
        return "".join(c for c in t if unicodedata.category(c) != "Mn")

    vistos: set[str] = set()
    posiciones: set[tuple[int, int]] = set()
    for pc in dto.pcs:
        nombre = pc.nombre.strip()
        if not nombre or len(nombre) > 50:
            raise bad_request("Nombre de PC vacio o demasiado largo (max 50)")
        if _norm(nombre) in vistos:
            raise bad_request(f"PC '{nombre}' duplicada")
        vistos.add(_norm(nombre))
        if not (0 <= pc.fila < max(dto.filas, 1) and 0 <= pc.col < max(dto.cols, 1)):
            raise bad_request(f"PC '{nombre}' fuera de la grilla (filas/columnas)")
        if (pc.fila, pc.col) in posiciones:
            raise bad_request(f"Dos PCs en la misma celda ({pc.fila},{pc.col})")
        posiciones.add((pc.fila, pc.col))
    pcs_previas = [
        {"nombre": p.nombre} for p in _pcs_de(db, lab_id)
    ]
    db.query(LabPc).filter(LabPc.laboratorio_id == lab_id).delete()
    previas = [p["nombre"] for p in pcs_previas]
    nuevas = [pc.nombre.strip() for pc in dto.pcs]
    if previas != sorted(nuevas) or len(previas) != len(nuevas):
        quitadas = sorted(set(previas) - set(nuevas))
        agregadas = sorted(set(nuevas) - set(previas))
        registrar(
            db,
            user,
            "editar",
            "pcs_lab",
            lab_id,
            f"PCs {len(previas)} -> {len(nuevas)}; "
            f"quitadas: {', '.join(quitadas) or '-'}; "
            f"agregadas: {', '.join(agregadas) or '-'}",
        )
    ahora = datetime.now(UTC)
    for pc in dto.pcs:
        db.add(
            LabPc(
                laboratorio_id=lab_id,
                nombre=pc.nombre.strip(),
                fila=pc.fila,
                col=pc.col,
                activa=pc.activa,
                created_at=ahora,
            )
        )
    lab.filas_pc = dto.filas
    lab.cols_pc = dto.cols
    db.commit()
    return {
        "filas": lab.filas_pc,
        "cols": lab.cols_pc,
        "pcs": [
            {
                "id": pc.id,
                "nombre": pc.nombre,
                "fila": pc.fila,
                "col": pc.col,
                "activa": pc.activa,
            }
            for pc in _pcs_de(db, lab_id)
        ],
    }
