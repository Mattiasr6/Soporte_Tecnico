"""Indexa el histórico de dev (solo lectura) en el Chroma de prod.

No toca la DB prod: solo suma documentos `hist_<id>` (sin colisión con `atencion_<id>`).
Solo filas con FechaRegistro < 2026-09-01 (prod ya cubre septiembre).

Uso (host, con el venv live):
    cd backend-fastapi
    DEV_DATABASE_URL='postgresql+psycopg://soporte:...@localhost:5433/soporte_dev' \
      .venv312/bin/python ../scripts/indexar_historico.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend-fastapi")

CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend-fastapi",
    "chroma_db",
)


def main() -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from datetime import date

    from app.models.atencion import Atencion
    from app.models.usuario import Usuario
    from app.services import ia_retrieval

    model, col = ia_retrieval._lazy()
    existentes = set(col.get(ids=None, include=[])["ids"])
    e = create_engine(os.environ["DEV_DATABASE_URL"])
    nuevas = 0
    with Session(e) as db:
        usuarios = {u.id: u.display_name for u in db.execute(select(Usuario)).scalars().all()}
        q = (
            select(Atencion)
            .where(Atencion.fecha_registro < date(2026, 9, 1))
            .order_by(Atencion.id)
        )
        for a in db.execute(q).scalars().all():
            pid = f"hist_{a.id}"
            if pid in existentes:
                continue
            ficha = (
                f"{a.descripcion or ''}\nSolución: {a.solucion or ''}"
                f"\nCategoría: {a.categoria or ''} · Área: {a.area_solicitante or ''}"
                f" · Medio: {a.medio_solicitud or ''}"
                f"\nRegistrada por: {usuarios.get(a.usuario_id, '—')}"
            )
            if a.observaciones:
                ficha += f"\nObservaciones: {a.observaciones}"
            pregunta = f"{a.descripcion or ''} {a.categoria or ''} {a.area_solicitante or ''}"
            col.add(
                ids=[pid],
                documents=[ficha],
                metadatas=[{
                    "source": pid,
                    "question": pregunta,
                    "titulo": a.descripcion or "",
                    "categoria": a.categoria or "",
                    "area": a.area_solicitante or "",
                }],
                embeddings=[model.encode([pregunta.lower()], normalize_embeddings=True)[0].tolist()],
            )
            nuevas += 1
    print(f"históricas nuevas: {nuevas}, total: {col.count()}")


if __name__ == "__main__":
    raise SystemExit(main())
