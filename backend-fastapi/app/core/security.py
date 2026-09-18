"""Identidad temporal S3: header X-User-Id (dev/tests). S5 la reemplaza por JWT."""

from fastapi import Header

from app.core.errors import unauthorized
from app.db.base import SessionLocal
from app.models.usuario import Usuario


def require_user(x_user_id: int | None = Header(default=None)) -> Usuario:
    if x_user_id is None:
        raise unauthorized("Falta X-User-Id")
    with SessionLocal() as db:
        user = db.get(Usuario, x_user_id)
        if user is None:
            raise unauthorized("Usuario inexistente")
        db.expunge(user)
        return user


def is_privileged(user: Usuario) -> bool:
    return user.role == "Jefe" or user.can_view_dashboard
