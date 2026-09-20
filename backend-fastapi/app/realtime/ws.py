import json
import logging
from datetime import datetime, timezone

import jwt
from app.core.config import settings
from app.db.base import SessionLocal
from app.models.horario import Horario
from app.models.usuario import Usuario
from app.realtime import hub
from app.services.estados import estado_efectivo
from app.services.tokens import validar_token
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

log = logging.getLogger("realtime")

router = APIRouter()


def _hhmm() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


def _autenticar(access_token: str | None) -> Usuario | None:
    if not access_token:
        return None
    try:
        payload = validar_token(access_token, settings.JWT_SECRET)
        uid = int(str(payload.get("sub")))
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return None
    with SessionLocal() as db:
        user = db.get(Usuario, uid)
        if user is None:
            return None
        db.expunge(user)
        return user


def _flip_connect(user: Usuario) -> str:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        actual = db.get(Usuario, user.id)
        estado = "ausente"
        if actual is not None:
            if actual.estado_actual == "Ausente":
                actual.estado_actual = "Disponible"
                actual.updated_at = now
                db.commit()
            horario = db.scalars(
                select(Horario).where(
                    Horario.usuario_id == user.id,
                    Horario.mes == now.month,
                    Horario.anio == now.year,
                )
            ).first()
            estado = estado_efectivo(actual.estado_actual, horario, now)
    return estado


def _flip_disconnect(user_id: int) -> str | None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        actual = db.get(Usuario, user_id)
        if actual is None or actual.estado_actual != "Disponible":
            return None
        actual.estado_actual = "Ausente"
        actual.updated_at = now
        db.commit()
        return actual.display_name


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket, access_token: str | None = None):
    user = _autenticar(access_token)
    if user is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    conn_id = await hub.registrar(ws, user.id, user.display_name, user.role)
    estado = _flip_connect(user)
    await hub.broadcast(
        {
            "type": "status_changed",
            "usuario_id": user.id,
            "nombre": user.display_name,
            "estado": estado,
            "motivo": None,
            "colaborador_nombre": None,
            "timestamp": _hhmm(),
        }
    )
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except ValueError:
                log.warning("WS %s: JSON inválido, se ignora", conn_id)
                continue
            if msg.get("type") == "send_message" and msg.get("message"):
                await hub.broadcast(
                    {
                        "type": "receive_message",
                        "nombre": user.display_name,
                        "role": user.role,
                        "message": str(msg["message"])[:2000],
                        "timestamp": _hhmm(),
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        uid = await hub.desregistrar(conn_id)
        if uid is not None and not await hub.tiene_otra_conexion(uid):
            nombre = _flip_disconnect(uid)
            if nombre is not None:
                await hub.broadcast(
                    {
                        "type": "status_changed",
                        "usuario_id": uid,
                        "nombre": nombre,
                        "estado": "ausente",
                        "motivo": None,
                        "colaborador_nombre": None,
                        "timestamp": _hhmm(),
                    }
                )
