"""Identidad por JWT Bearer compatible .NET (S5)."""

from typing import Annotated

import jwt
from fastapi import Depends, Header

from app.core.config import settings
from app.core.errors import unauthorized
from app.db.base import SessionLocal
from app.models.usuario import Usuario
from app.services.tokens import CLAIM_VERSION, validar_token


def motivo_de_rechazo(payload: dict[str, object], user: Usuario) -> str | None:
    """Por qué hay que rechazar esta sesión, o None si sigue valiendo.

    Vive acá y no en cada guard para que el HTTP y el WebSocket no se desincronicen.
    """
    if not user.activo:
        return "Usuario desactivado"
    emitida = payload.get(CLAIM_VERSION)
    if isinstance(emitida, int) and emitida != user.token_version:
        return "Tu contraseña cambió: volvé a entrar"
    return None


def require_user(authorization: str | None = Header(default=None)) -> Usuario:
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized("Falta token Bearer")
    try:
        payload = validar_token(authorization[7:], settings.JWT_SECRET)
    except jwt.InvalidTokenError:
        raise unauthorized("Token inválido o expirado") from None
    sub = payload.get("sub")
    try:
        uid = int(str(sub))
    except (TypeError, ValueError):
        raise unauthorized("Token inválido o expirado") from None
    with SessionLocal() as db:
        user = db.get(Usuario, uid)
        if user is None:
            raise unauthorized("Usuario inexistente")
        motivo = motivo_de_rechazo(payload, user)
        if motivo is not None:
            raise unauthorized(motivo)
        db.expunge(user)
        return user


def is_privileged(user: Usuario) -> bool:
    return user.role == "Jefe" or user.can_view_dashboard


CurrentUser = Annotated[Usuario, Depends(require_user)]
