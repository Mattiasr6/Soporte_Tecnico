"""Smoke live S8: FastAPI :5002 + convivencia .NET :5001 misma DB. Solo lectura (+WS efímero).

Uso desde backend-fastapi/:  .venv/bin/python scripts/smoke_live.py
Requiere .env (DATABASE_URL, JWT_SECRET, SEED_PASSWORD) y servicios arriba.
"""

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

import websockets

PY = "http://localhost:5002"
NET = "http://localhost:5001"
WS = "ws://localhost:5002/ws"

EMAILS = {
    "mattias": "mattias.ribera@upds.edu.bo",
    "diego": "diego.orihuela@upds.edu.bo",
    "jefe": "josue.huayllas@upds.edu.bo",
}
PASSWORD = os.environ["SEED_PASSWORD"]

resultados: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    resultados.append((nombre, ok, detalle))
    print(f"[{'OK' if ok else 'FAIL'}] {nombre} {detalle}")


def api(
    base: str,
    path: str,
    token: str | None = None,
    method: str | None = None,
    body: dict[str, object] | None = None,
) -> tuple[int, object]:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,  # type: ignore[arg-type]
        headers={"Content-Type": "application/json"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def login(base: str, email: str) -> str:
    status, data = api(
        base, "/api/auth/login", body={"email": email, "password": PASSWORD}
    )
    assert status == 200, f"login {base} {email}: {status} {data}"
    assert isinstance(data, dict)
    token = data["token"]
    assert isinstance(token, str)
    return token


async def check_ws(token: str) -> None:
    async with websockets.connect(f"{WS}?access_token={token}") as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        assert isinstance(raw, str)
        ev = json.loads(raw)
        check(
            "ws status_changed al conectar",
            ev.get("type") == "status_changed",
            str(ev.get("estado")),
        )
        await ws.send(json.dumps({"type": "send_message", "message": "smoke S8"}))
        raw2 = await asyncio.wait_for(ws.recv(), timeout=10)
        assert isinstance(raw2, str)
        eco = json.loads(raw2)
        check(
            "ws eco send_message",
            eco.get("type") == "receive_message" and eco.get("message") == "smoke S8",
        )


def main() -> int:
    status, data = api(PY, "/health")
    check(
        "health",
        status == 200 and isinstance(data, dict) and data.get("db") == "up",
        str(data),
    )

    t_mattias = login(PY, EMAILS["mattias"])
    t_diego = login(PY, EMAILS["diego"])
    t_jefe = login(PY, EMAILS["jefe"])
    check("login x3", True)

    status, arbol = api(PY, "/api/jerarquia/arbol", t_mattias)
    assert isinstance(arbol, dict)
    check(
        "arbol 3/4/53",
        status == 200
        and len(arbol["padres"]) == 3
        and len(arbol["grupos"]) == 4
        and len(arbol["areas"]) == 53,
        f"padres={len(arbol['padres'])} grupos={len(arbol['grupos'])} areas={len(arbol['areas'])}",
    )

    status, propias = api(PY, "/api/atenciones", t_diego)
    assert isinstance(propias, list)
    check(
        "diego solo propias",
        status == 200
        and len(propias) > 0
        and all(a["usuario_id"] == 2 for a in propias),
        f"n={len(propias)}",
    )

    status, filtradas = api(PY, "/api/atenciones?usuario_id=1", t_jefe)
    assert isinstance(filtradas, list)
    check(
        "jefe filtra",
        status == 200
        and len(filtradas) > 0
        and all(a["usuario_id"] == 1 for a in filtradas),
    )

    asyncio.run(check_ws(t_diego))
    _, me = api(PY, "/api/usuarios/me", t_diego)
    assert isinstance(me, dict)
    check(
        "diego vuelve a ausente tras WS",
        me.get("estado_actual") == "ausente",
        str(me.get("estado_actual")),
    )

    # Convivencia .NET
    t_net = login(NET, EMAILS["jefe"])
    check("login .NET con misma clave", True)
    status, arbol_net = api(NET, "/api/jerarquia/arbol", t_net)
    assert isinstance(arbol_net, dict)
    check(
        "conteo .NET == Python",
        status == 200 and len(arbol_net["areas"]) == len(arbol["areas"]),
        f"net={len(arbol_net['areas'])} py={len(arbol['areas'])}",
    )
    status, _ = api(NET, "/api/jerarquia/arbol", t_mattias)
    check("JWT python aceptado por .NET", status == 200, f"http={status}")

    fallos = [n for n, ok, _ in resultados if not ok]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} checks verdes")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
