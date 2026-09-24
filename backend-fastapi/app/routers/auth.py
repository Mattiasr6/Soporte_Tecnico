from datetime import UTC, datetime

import bcrypt
from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.errors import bad_request, forbidden, not_found, unauthorized
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.usuario import Usuario
from app.schemas.auth import LoginIn, LoginOut, PasswordIn
from app.services.tokens import crear_token

MINIMO_PASSWORD = 8

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(dto: LoginIn, db: DbSession):
    email = dto.email.strip().lower()
    user = db.scalars(select(Usuario).where(func.lower(Usuario.email) == email)).first()
    if user is None:
        raise unauthorized("Correo no registrado")
    if not user.activo:
        raise forbidden("Usuario desactivado")
    if not user.password_hash:
        raise unauthorized(
            "Este usuario no tiene contraseña asignada. Contacta al administrador."
        )
    if not bcrypt.checkpw(dto.password.encode(), user.password_hash.encode()):
        raise unauthorized("Contraseña incorrecta")
    from app.core.config import settings

    token = crear_token(
        user.id, user.display_name, user.role, user.email, settings.JWT_SECRET
    )
    return {
        "token": token,
        "user": {
            "id": user.id,
            "display_name": user.display_name,
            "role": user.role,
            "email": user.email,
            "estado_actual": user.estado_actual,
            "can_view_dashboard": user.can_view_dashboard,
        },
    }


@router.post("/password", status_code=204)
def cambiar_password(dto: PasswordIn, db: DbSession, user: CurrentUser) -> None:
    """Cada uno cambia su propia contraseña: nunca la de otro."""
    if len(dto.nueva) < MINIMO_PASSWORD:
        raise bad_request(
            f"La contraseña nueva necesita al menos {MINIMO_PASSWORD} caracteres"
        )
    if dto.nueva == dto.actual:
        raise bad_request("La contraseña nueva tiene que ser distinta a la actual")
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise not_found("Usuario no encontrado")
    if not usuario.password_hash or not bcrypt.checkpw(
        dto.actual.encode(), usuario.password_hash.encode()
    ):
        raise unauthorized("La contraseña actual no coincide")
    usuario.password_hash = bcrypt.hashpw(dto.nueva.encode(), bcrypt.gensalt()).decode()
    usuario.updated_at = datetime.now(UTC)
    db.commit()
