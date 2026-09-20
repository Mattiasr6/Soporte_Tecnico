import bcrypt
from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.errors import unauthorized
from app.db.session import DbSession
from app.models.usuario import Usuario
from app.schemas.auth import LoginIn, LoginOut
from app.services.tokens import crear_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(dto: LoginIn, db: DbSession):
    email = dto.email.strip().lower()
    user = db.scalars(select(Usuario).where(func.lower(Usuario.email) == email)).first()
    if user is None:
        raise unauthorized("Correo no registrado")
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
