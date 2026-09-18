"""Registry WS en memoria + broadcasts.

Dev: correr uvicorn con 1 worker. Multi-worker requiere pubsub externo (fuera S7).
"""

import asyncio
import logging
import uuid

from fastapi import WebSocket

log = logging.getLogger("realtime")

_conexiones: dict[str, tuple["WebSocket", int, str, str]] = {}
_lock = asyncio.Lock()


async def registrar(ws: WebSocket, user_id: int, nombre: str, role: str) -> str:
    conn_id = uuid.uuid4().hex
    async with _lock:
        _conexiones[conn_id] = (ws, user_id, nombre, role)
    return conn_id


async def desregistrar(conn_id: str) -> int | None:
    async with _lock:
        registro = _conexiones.pop(conn_id, None)
    return registro[1] if registro else None


async def tiene_otra_conexion(user_id: int) -> bool:
    async with _lock:
        return any(uid == user_id for _, uid, _, _ in _conexiones.values())


async def broadcast(mensaje: dict[str, object]) -> None:
    async with _lock:
        destinos = list(_conexiones.items())
    for conn_id, (ws, _, _, _) in destinos:
        try:
            await ws.send_json(mensaje)
        except Exception:  # noqa: BLE001 — cualquier socket muerto se retira
            log.warning("WS %s caído, se retira", conn_id)
            await desregistrar(conn_id)
