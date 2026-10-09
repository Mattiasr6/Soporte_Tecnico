"""Shift report photos on disk (replaces the Supabase Storage bucket `reportes-turno`).

Same approach as Soporte's `data/aux_reportes`: JPG/PNG/WEBP up to 5 MB, decoded
with Pillow and re-encoded as WebP (drops metadata, rejects non-images), stored
under `<ASIGNACION_DATA_DIR>/reportes-turno/YYYY-MM/<uuid>.webp`. The DB keeps
the relative path; file names are generated here, never taken from the client.
"""

import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.services.asignacion.sql import error_detail

MAX_BYTES = 5 * 1024 * 1024
TIPOS = ("image/jpeg", "image/png", "image/webp")
_WEBP_CALIDAD = 80
_DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "asignacion"
CARPETA = "reportes-turno"


def base_dir() -> Path:
    root = (
        Path(settings.ASIGNACION_DATA_DIR)
        if settings.ASIGNACION_DATA_DIR
        else _DEFAULT_DIR
    )
    return (root / CARPETA).resolve()


def resolve(relative: str) -> Path | None:
    """Absolute path of a stored photo, or None if it would escape the folder."""
    base = base_dir()
    path = (base / relative).resolve()
    return path if path.is_relative_to(base) and path != base else None


def guardar(content_type: str | None, contenido: bytes) -> str:
    """Validate and store one photo; returns its relative path."""
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
    destino = base_dir() / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(buf.getvalue())
    return relativo


def borrar(relativos: list[str | None]) -> None:
    """Remove stored photos; unknown or unsafe paths are ignored."""
    for relativo in relativos:
        if not relativo:
            continue
        path = resolve(relativo)
        if path is not None:
            path.unlink(missing_ok=True)
