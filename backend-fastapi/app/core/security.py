"""Identidad por JWT Bearer compatible .NET (S5)."""

from typing import Annotated

import jwt
from fastapi import Depends, Header

from app.core.config import settings
from app.core.errors import unauthorized
from app.db.base import SessionLocal
from app.models.usuario import Usuario
from app.services.tokens import validar_token


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
        if not user.activo:
            raise unauthorized("Usuario desactivado")
        db.expunge(user)
        return user


def is_privileged(user: Usuario) -> bool:
    return user.role == "Jefe" or user.can_view_dashboard


CurrentUser = Annotated[Usuario, Depends(require_user)]
