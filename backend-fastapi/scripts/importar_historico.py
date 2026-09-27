"""Importa las atenciones historicas de los 2 tecnicos retirados (Excel 2026).

Uso desde backend-fastapi/:
    python scripts/importar_historico.py
    ATENCIONES_CSV=atenciones_historico.csv python scripts/actualizar_atenciones.py

Las fuentes viven en docs/csv/ (fuera de versionado) y su formato no es el de carga: no
traen hora, ni tecnico, ni colaborador, y las fechas vienen con anios mal tipeados. Este
script traduce ese formato al que seed_atenciones() ya espera. Ver
docs/import-historico-decisiones.md para el mapeo de areas y las reglas de negocio.
"""

import csv
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.db.base import SessionLocal
from app.models.atencion import Atencion
from app.models.usuario import Usuario
from app.services.categorias import CATEGORIAS_VALIDAS
from app.services.csv_import import MEDIOS_VALIDOS, SOLICITANTES_VALIDOS
from app.services.horarios import LA_PAZ
from scripts.extraer_septiembre import _norm, construir_resolutor

RAIZ = Path(__file__).resolve().parents[2]
FUENTES = RAIZ / "docs" / "csv"
SALIDA = RAIZ / "atenciones_historico.csv"
ANIO = 2026
PRIMER_MES_VALIDO = 1
ULTIMO_MES_VALIDO = 4

COLUMNAS = [
    "tecnico_email",
    "area_codigo",
    "colaborador_email",
    "medio_solicitud",
    "usuario_solicitante",
    "categoria",
    "descripcion",
    "solucion",
    "observaciones",
    "enlace_apoyo",
    "fuera_de_turno",
    "fecha_registro",
    "created_at",
]

ARCHIVOS = [
    (
        "GABRIEL",
        "gabriel.torrico@upds.edu.bo",
        "Atención al Cliente - Soporte técnico(Gabriel).csv",
    ),
    (
        "DEYMAR",
        "deymar.lozano@upds.edu.bo",
        "Atención al Cliente - Soporte técnico(Deymar).csv",
    ),
]

# El area quedo mal copiada en 3 filas; la descripcion dice el area real.
CORRECCIONES_AREA = {
    ("DEYMAR", "50"): "SFIC",
    ("GABRIEL", "201"): "Académicos Modular",
    ("GABRIEL", "287"): "Cardio Salud",
}

# ID consecutivo al anterior con todos los campos identicos.
DESCARTES = {("GABRIEL", "363")}

EQUIVALENCIAS_MEDIO = {"Correo": "Interno"}

COL_AREA = "Área solicitante"
COL_SOLICITANTE = "Usuario Solicitante\n(ADM/BEC)"
COL_MEDIO = "Medio de Solicitud"
COL_CATEGORIA = "Categoría Incidente"
COL_DESCRIPCION = "Descripción / detalle"
COL_SOLUCION = "Solución / acciones"
COL_OBSERVACIONES = "Observaciones"
COL_ENLACE = "Enlace de Apoyo"

VACIOS = {"", "N/A", "NA"}


@dataclass
class Fila:
    tecnico_email: str
    area_codigo: str
    medio_solicitud: str
    usuario_solicitante: str
    categoria: str
    descripcion: str
    solucion: str
    observaciones: str
    enlace_apoyo: str
    fecha_registro: date
    colaborador_email: str = ""
    fuera_de_turno: str = "false"
    created_at: str = ""


def _texto(fila: dict[str, str], columna: str) -> str:
    return (fila.get(columna) or "").strip()


def _opcional(fila: dict[str, str], columna: str) -> str:
    valor = _texto(fila, columna)
    return "" if valor.upper() in VACIOS else valor


def _fecha(
    fila: dict[str, str], clave: str, id_: str, avisos: list[str], errores: list[str]
) -> date | None:
    crudo = _texto(fila, "Fecha")
    try:
        dia_num, mes, anio = (int(parte) for parte in crudo.split("/"))
        dia = date(anio, mes, dia_num)
    except ValueError:
        errores.append(f"fecha invalida: archivo={clave} id={id_} valor={crudo!r}")
        return None
    if dia.year != ANIO:
        avisos.append(f"anio corregido: archivo={clave} id={id_} {crudo} -> {ANIO}")
        dia = dia.replace(year=ANIO)
    if not PRIMER_MES_VALIDO <= dia.month <= ULTIMO_MES_VALIDO:
        errores.append(f"fecha fuera de rango: archivo={clave} id={id_} {dia}")
        return None
    return dia


def _leer(archivo: str) -> list[dict[str, str]]:
    with open(FUENTES / archivo, encoding="latin-1", newline="") as f:
        return [
            fila
            for fila in csv.DictReader(f, delimiter=";")
            if (fila.get("ID") or "").strip()
        ]


def construir() -> tuple[list[Fila], list[str], int]:
    resolutor = construir_resolutor()
    normalizado = {_norm(k): v for k, v in resolutor.items()}
    avisos: list[str] = []
    errores: list[str] = []
    filas: list[Fila] = []
    descartadas = 0

    for clave, email, archivo in ARCHIVOS:
        for cruda in _leer(archivo):
            id_ = _texto(cruda, "ID")
            if (clave, id_) in DESCARTES:
                descartadas += 1
                continue

            dia = _fecha(cruda, clave, id_, avisos, errores)
            if dia is None:
                continue

            area_cruda = _texto(cruda, COL_AREA)
            origen_area = CORRECCIONES_AREA.get((clave, id_), area_cruda)
            if origen_area != area_cruda:
                avisos.append(
                    f"area corregida: archivo={clave} id={id_}"
                    f" {area_cruda!r} -> {origen_area!r}"
                )
            codigo = resolutor.get(origen_area) or normalizado.get(_norm(origen_area))
            if codigo is None:
                errores.append(
                    f"area sin resolver: archivo={clave} id={id_} valor={origen_area!r}"
                )
                continue

            medio_crudo = _texto(cruda, COL_MEDIO)
            medio = EQUIVALENCIAS_MEDIO.get(medio_crudo, medio_crudo)
            if medio != medio_crudo:
                avisos.append(
                    f"medio normalizado: archivo={clave} id={id_}"
                    f" {medio_crudo!r} -> {medio!r}"
                )
            if medio not in MEDIOS_VALIDOS:
                errores.append(
                    f"medio invalido: archivo={clave} id={id_} valor={medio!r}"
                )
                continue

            solicitante = _texto(cruda, COL_SOLICITANTE)
            if solicitante not in SOLICITANTES_VALIDOS:
                errores.append(
                    f"solicitante invalido: archivo={clave} id={id_}"
                    f" valor={solicitante!r}"
                )
                continue

            categoria = _texto(cruda, COL_CATEGORIA)
            if categoria not in CATEGORIAS_VALIDAS:
                errores.append(
                    f"categoria invalida: archivo={clave} id={id_} valor={categoria!r}"
                )
                continue

            filas.append(
                Fila(
                    tecnico_email=email,
                    area_codigo=codigo,
                    medio_solicitud=medio,
                    usuario_solicitante=solicitante,
                    categoria=categoria,
                    descripcion=_texto(cruda, COL_DESCRIPCION),
                    solucion=_texto(cruda, COL_SOLUCION),
                    observaciones=_opcional(cruda, COL_OBSERVACIONES),
                    enlace_apoyo=_opcional(cruda, COL_ENLACE),
                    fecha_registro=dia,
                )
            )

    if errores:
        for e in errores:
            print(f"  - {e}", file=sys.stderr)
        raise SystemExit(f"{len(errores)} errores: no se genero el CSV")

    _derivar_created_at(filas)
    return filas, avisos, descartadas


def _derivar_created_at(filas: list[Fila]) -> None:
    """El origen no trae hora: 12:00 de La Paz + k segundos dentro del dia.

    Determinista y re-ejecutable: dos corridas producen los mismos created_at, que es la
    clave de idempotencia de seed_atenciones(). k alcanza porque el dia mas cargado
    tiene 16 filas.
    """
    por_dia: dict[date, list[Fila]] = {}
    for fila in filas:
        por_dia.setdefault(fila.fecha_registro, []).append(fila)
    for dia, grupo in por_dia.items():
        grupo.sort(
            key=lambda f: (f.tecnico_email, f.area_codigo, f.descripcion, f.solucion)
        )
        for k, fila in enumerate(grupo):
            mediodia = datetime(dia.year, dia.month, dia.day, 12, tzinfo=LA_PAZ)
            fila.created_at = (
                (mediodia + timedelta(seconds=k)).astimezone(UTC).isoformat()
            )


def _verificar_colisiones(filas: list[Fila]) -> None:
    """Aborta si un created_at derivado pisa una fila que no es de estos 2 tecnicos."""
    emails = {email for _, email, _ in ARCHIVOS}
    with SessionLocal() as db:
        ids = {u.email: u.id for u in db.scalars(select(Usuario)).all()}
        faltan = sorted(emails - ids.keys())
        if faltan:
            raise SystemExit(
                f"Tecnico no existe en Usuarios: {faltan}."
                " Crealos primero (POST /api/usuarios)."
            )
        propios = {ids[e] for e in emails}
        existentes: dict[datetime, tuple[int, date]] = {
            creado: (usuario_id, fecha)
            for creado, usuario_id, fecha in db.execute(
                select(
                    Atencion.created_at, Atencion.usuario_id, Atencion.fecha_registro
                )
            ).all()
        }
    choques = []
    for fila in filas:
        dueno = existentes.get(datetime.fromisoformat(fila.created_at))
        if dueno is None:
            continue
        if dueno[0] in propios and dueno[1] == fila.fecha_registro:
            continue
        choques.append(f"{fila.created_at} (tecnico={fila.tecnico_email})")
    if choques:
        for c in choques:
            print(f"  - {c}", file=sys.stderr)
        raise SystemExit(f"{len(choques)} colisiones de created_at con filas ajenas")


def main() -> int:
    filas, avisos, descartadas = construir()
    print(f"filas a cargar: {len(filas)} | descartadas: {descartadas}")

    _verificar_colisiones(filas)

    with open(SALIDA, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(
                {**asdict(fila), "fecha_registro": fila.fecha_registro.isoformat()}
            )

    por_tecnico: dict[str, int] = {}
    por_mes: dict[str, int] = {}
    for fila in filas:
        por_tecnico[fila.tecnico_email] = por_tecnico.get(fila.tecnico_email, 0) + 1
        mes = f"{fila.fecha_registro.year}-{fila.fecha_registro.month:02d}"
        por_mes[mes] = por_mes.get(mes, 0) + 1

    print(f"escrito: {SALIDA.name}")
    for email, total in sorted(por_tecnico.items()):
        print(f"  {email:32s} {total}")
    print(f"  por mes: {dict(sorted(por_mes.items()))}")
    print(f"  areas canonicas: {len({f.area_codigo for f in filas})}")
    print(f"  con observaciones: {sum(1 for f in filas if f.observaciones)}")
    if avisos:
        print(f"\nnormalizaciones aplicadas ({len(avisos)}):")
        for a in avisos:
            print(f"  - {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
