"""Tools de atenciones: lectura + escritura con confirmación (RN-01..RN-03)."""

from typing import Any

from .client import api

WILMERCITO_EMAIL = "wilmercito@sistema.upds.edu.bo"


def _wilmercito_id(jwt: str) -> int | None:
    for u in api("GET", "/api/usuarios?incluir_inactivos=true", jwt):
        if isinstance(u, dict) and u.get("email") == WILMERCITO_EMAIL:
            return u.get("id")
    return None


def soporte_buscar_atenciones(jwt: str, texto: str, top_k: int = 3) -> Any:
    """Busca atenciones pasadas parecidas a un problema."""
    return api("POST", "/api/ia/buscar", jwt, {"texto": texto, "top_k": top_k})


def soporte_get_atencion(jwt: str, atencion_id: int) -> Any:
    """Ficha de una atención por id (usa retrieval indexado)."""
    from app.services import ia_retrieval

    doc = ia_retrieval.por_id(f"atencion_{atencion_id}")
    if doc is None:
        return {"ok": False, "detail": "no-existe"}
    return {"ok": True, **doc}


def soporte_crear_borrador(
    jwt: str,
    descripcion: str,
    categoria: str,
    area_solicitante: str = "",
    medio_solicitud: str = "Interno",
    usuario_solicitante: str = "EST",
    solucion: str = "",
    observaciones: str | None = None,
) -> dict[str, Any]:
    """Arma el borrador SIN guardar. El humano debe confirmar después."""
    return {
        "preview": {
            "descripcion": descripcion,
            "categoria": categoria,
            "area_solicitante": area_solicitante,
            "medio_solicitud": medio_solicitud,
            "usuario_solicitante": usuario_solicitante,
            "solucion": solucion or "Pendiente de atención.",
            "observaciones": observaciones,
            "colaborador_id": _wilmercito_id(jwt),
        },
        "requiere_confirm": True,
    }


def soporte_confirmar_creacion(
    jwt: str, borrador: dict[str, Any], confirm: bool = False
) -> Any:
    """Guarda el borrador. Exige confirm:true. Autor = dueño del JWT."""
    if confirm is not True:
        return {"ok": False, "detail": "requiere_confirm"}
    borrador = dict(borrador)
    borrador["colaborador_id"] = _wilmercito_id(jwt)
    return api("POST", "/api/atenciones/batch", jwt, {"atenciones": [borrador]})


def soporte_actualizar_atencion(
    jwt: str, atencion_id: int, cambios: dict[str, Any], confirm: bool = False
) -> Any:
    """Edita una atención (solo dueño). Exige confirm:true."""
    if confirm is not True:
        return {"ok": False, "detail": "requiere_confirm"}
    return api("PUT", f"/api/atenciones/{atencion_id}", jwt, cambios)


def soporte_reclasificar(
    jwt: str, atencion_id: int, area_id: int, confirm: bool = False
) -> Any:
    """Reclasifica por área (jefe). Exige confirm:true."""
    if confirm is not True:
        return {"ok": False, "detail": "requiere_confirm"}
    return api(
        "PATCH", f"/api/atenciones/{atencion_id}/jerarquia", jwt, {"area_id": area_id}
    )
