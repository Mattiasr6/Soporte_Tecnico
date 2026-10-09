from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.realtime.ws import router as ws_router
from app.routers import (
    announcements,
    areas,
    asignacion,
    atenciones,
    auditoria,
    auth,
    horarios,
    ia,
    jerarquia,
    laboratorios,
    novedades,
    software,
    sugerencias,
    usuarios,
)


def configure_cors(target: FastAPI, origins: list[str]) -> None:
    """Allow browser calls from `origins` (e.g. the Angular dev server).

    No origins means no middleware: same behaviour as before CORS_ORIGINS existed.
    """
    if not origins:
        return
    target.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )


app = FastAPI(title="Soporte Tecnico API (Python)")
configure_cors(app, settings.cors_origin_list)
app.include_router(ws_router)
app.include_router(jerarquia.router)
app.include_router(sugerencias.router)
app.include_router(areas.router)
app.include_router(asignacion.router)
app.include_router(auth.router)
app.include_router(horarios.router)
app.include_router(ia.router)
app.include_router(usuarios.router)
app.include_router(announcements.router)
app.include_router(atenciones.router)
app.include_router(laboratorios.router)
app.include_router(novedades.router)
app.include_router(software.router)
app.include_router(auditoria.router)


@app.get("/health")
def health(db: Annotated[Session, Depends(get_db)]):
    try:
        _ = db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except SQLAlchemyError:
        return {"status": "degraded", "db": "down"}
