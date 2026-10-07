"""Rastro de cambios esenciales: quién tocó qué y qué se borró.

`registrar` solo encola la fila; el commit lo hace el endpoint que ya estaba
transaccionando, así un fallo de auditoría no parte la operación en dos.
"""

from datetime import UTC, datetime
from typing import Any

from app.models.auditoria import AuditoriaCambio
from app.models.usuario import Usuario


def registrar(
    db: Any,
    user: Usuario,
    accion: str,
    entidad: str,
    entidad_id: int | None = None,
    detalle: str = "",
) -> None:
    db.add(
        AuditoriaCambio(
            fecha=datetime.now(UTC),
            usuario_id=user.id,
            usuario_email=user.email or "",
            usuario_nombre=user.display_name or "",
            rol=user.role or "",
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle[:4000],
            created_at=datetime.now(UTC),
        )
    )


def diff(antes: dict[str, Any], despues: dict[str, Any]) -> str:
    """Campos que cambiaron, en texto legible: 'ram: 4 GB -> 8 GB'."""
    partes = []
    for k in antes:
        viejo, nuevo = antes[k], despues.get(k)
        if viejo != nuevo:
            partes.append(f"{k}: {viejo!r} -> {nuevo!r}")
    return "; ".join(partes)
