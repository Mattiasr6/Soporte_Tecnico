from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routers import areas, atenciones, jerarquia

app = FastAPI(title="Soporte Tecnico API (Python)")
app.include_router(jerarquia.router)
app.include_router(areas.router)
app.include_router(atenciones.router)


@app.get("/health")
def health(db: Annotated[Session, Depends(get_db)]):
    try:
        _ = db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except SQLAlchemyError:
        return {"status": "degraded", "db": "down"}
