"""Cliente HTTP interno hacia la API (127.0.0.1:5012) con JWT passthrough."""

import os
from typing import Any

import httpx

BASE = os.environ.get("MCP_API_URL", "http://127.0.0.1:5012").rstrip("/")


def api(method: str, path: str, jwt: str, body: dict[str, Any] | None = None) -> Any:
    """Llama a la API con el JWT del técnico. Cero bypass de roles."""
    r = httpx.request(
        method,
        BASE + path,
        headers={"Authorization": f"Bearer {jwt}"},
        json=body,
        timeout=120,
    )
    if r.status_code == 204:
        return {"ok": True}
    r.raise_for_status()
    return r.json()
