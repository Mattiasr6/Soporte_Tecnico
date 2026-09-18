"""Parseo puro del CSV legacy (RN-S4-01..04). Sin DB: testeable sin efectos."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.services.categorias import CATEGORIAS_VALIDAS, normalizar_categoria

MEDIOS_VALIDOS = frozenset({"Presencial", "Interno", "WhatsApp", "E-ticket"})
SOLICITANTES_VALIDOS = frozenset({"ADM", "BEC", "DOC", "EST"})


@dataclass
class FilaCsv:
    area: str
    medio: str
    usuario_solicitante: str
    categoria: str
    descripcion: str
    solucion: str
    observaciones: str | None
    enlace: str | None
    fecha: date


def detectar_encoding(raw: bytes) -> str:
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    if raw[:2] == b"\xff\xfe":
        return "utf-16-le"
    if raw[:2] == b"\xfe\xff":
        return "utf-16-be"
    return "latin-1"


def _fecha_o_hoy(raw: str) -> date:
    try:
        dia, mes, anio = raw.split("/")
        return date(int(anio), int(mes), int(dia))
    except ValueError:
        return datetime.now(timezone.utc).date()


def _o_null(valor: str) -> str | None:
    return None if valor in ("N/A", "") else valor


def parse_csv(contenido: bytes) -> tuple[list[FilaCsv], list[str]]:
    texto = contenido.decode(detectar_encoding(contenido[:4]))
    filas: list[FilaCsv] = []
    errores: list[str] = []
    for numero, linea in enumerate(texto.splitlines()[1:], start=2):
        partes = linea.split(";")
        if len(partes) < 8:
            continue
        try:
            int(partes[0].strip())
        except ValueError:
            continue
        area = partes[2].strip()
        medio = partes[4].strip()
        solicitante = partes[3].strip()
        categoria = partes[5].strip()
        descripcion = partes[6].strip()
        solucion = partes[7].strip()
        if not area or not descripcion or not solucion:
            errores.append(f"Línea {numero}: faltan campos obligatorios")
            continue
        cat = normalizar_categoria(categoria)
        if cat not in CATEGORIAS_VALIDAS:
            errores.append(
                f"Línea {numero}: categoría inválida '{categoria}', se usará 'Otros'"
            )
            cat = "Otros"
        filas.append(
            FilaCsv(
                area=area,
                medio=medio if medio in MEDIOS_VALIDOS else "Interno",
                usuario_solicitante=(
                    solicitante if solicitante in SOLICITANTES_VALIDOS else "ADM"
                ),
                categoria=cat,
                descripcion=descripcion,
                solucion=solucion,
                observaciones=_o_null(partes[8].strip()) if len(partes) > 8 else None,
                enlace=_o_null(partes[9].strip()) if len(partes) > 9 else None,
                fecha=_fecha_o_hoy(partes[1].strip()),
            )
        )
    return filas, errores
