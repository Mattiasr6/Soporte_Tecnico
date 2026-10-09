"""Photos on disk (replace the Supabase Storage buckets `reportes-turno` and
`objetos-perdidos`).

Same approach as Soporte's `data/aux_reportes`: JPG/PNG/WEBP up to 5 MB, decoded
with Pillow and re-encoded as WebP (drops metadata, rejects non-images), stored
under `<ASIGNACION_DATA_DIR>/<bucket>/[<prefix>/]YYYY-MM/<uuid>.webp`. The DB
keeps the path relative to the bucket folder; file names are generated here,
never taken from the client.
"""

import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.services.asignacion.sql import error_detail, not_found

MAX_BYTES = 5 * 1024 * 1024
TIPOS = ("image/jpeg", "image/png", "image/webp")
_WEBP_CALIDAD = 80
_DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "asignacion"
CARPETA = "reportes-turno"
CARPETA_OBJETOS = "objetos-perdidos"


def base_dir(carpeta: str = CARPETA) -> Path:
    root = (
        Path(settings.ASIGNACION_DATA_DIR)
        if settings.ASIGNACION_DATA_DIR
        else _DEFAULT_DIR
    )
    return (root / carpeta).resolve()


def resolve(relative: str, carpeta: str = CARPETA) -> Path | None:
    """Absolute path of a stored photo, or None if it would escape the folder."""
    base = base_dir(carpeta)
    path = (base / relative).resolve()
    return path if path.is_relative_to(base) and path != base else None


def guardar(
    content_type: str | None,
    contenido: bytes,
    carpeta: str = CARPETA,
    prefijo: str | None = None,
) -> str:
    """Validate and store one photo; returns its path relative to `carpeta`."""
    if (content_type or "").lower() not in TIPOS:
        raise HTTPException(
            415, error_detail("La foto debe ser JPG, PNG o WEBP.", None)
        )
    if not contenido:
        raise HTTPException(422, error_detail("La foto está vacía.", None))
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, error_detail("La foto supera los 5 MB.", None))
    try:
        with Image.open(io.BytesIO(contenido)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "WEBP", quality=_WEBP_CALIDAD)
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ):
        raise HTTPException(
            422, error_detail("La foto no es una imagen válida.", None)
        ) from None
    relativo = f"{datetime.now(UTC):%Y-%m}/{uuid.uuid4().hex}.webp"
    if prefijo:
        relativo = f"{prefijo}/{relativo}"
    destino = base_dir(carpeta) / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(buf.getvalue())
    return relativo


def borrar(relativos: list[str | None], carpeta: str = CARPETA) -> None:
    """Remove stored photos; unknown or unsafe paths are ignored."""
    for relativo in relativos:
        if not relativo:
            continue
        path = resolve(relativo, carpeta)
        if path is not None:
            path.unlink(missing_ok=True)


_MEDIA_TYPES = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def servir(relativo: str | None, carpeta: str = CARPETA) -> FileResponse:
    """Private (no-store) response with a stored photo; 404 if it is missing."""
    path = resolve(relativo, carpeta) if relativo else None
    if path is None or not path.is_file():
        raise not_found()
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"),
        headers={"Cache-Control": "private, no-store"},
    )
