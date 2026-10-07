"""Siembra PCs de un laboratorio con el patrón SCPC {base}+i (ej: lab 10 -> 1001..).

Uso (dentro del container api):
  DATABASE_URL=... python scripts/seed_lab_pcs.py <lab_id> <base> <cantidad> <cols>

Respeta las PCs que ya existen (no duplica) y acomoda en grilla cols-por-fila.
"""
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.lab_pc import LabPc
from app.models.laboratorio import Laboratorio


def main() -> None:
    lab_id, base, cantidad, cols = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    with SessionLocal() as db:
        lab = db.get(Laboratorio, lab_id)
        assert lab is not None, f"lab {lab_id} no existe"
        existentes = {
            p.nombre
            for p in db.scalars(
                select(LabPc).where(LabPc.laboratorio_id == lab_id)
            ).all()
        }
        filas_exist = {
            (p.fila, p.col)
            for p in db.scalars(
                select(LabPc).where(LabPc.laboratorio_id == lab_id)
            ).all()
        }
        creadas = 0
        i = 1
        while creadas < cantidad:
            nombre = f"SCPC {base + i}"
            i += 1
            if nombre in existentes:
                continue
            idx = len(existentes) + creadas
            fila, col = divmod(idx, cols)
            while (fila, col) in filas_exist:
                idx += 1
                fila, col = divmod(idx, cols)
            db.add(
                LabPc(
                    laboratorio_id=lab_id,
                    nombre=nombre,
                    fila=fila,
                    col=col,
                    activa=True,
                    created_at=datetime.now(UTC),
                )
            )
            filas_exist.add((fila, col))
            creadas += 1
        total = len(existentes) + creadas
        lab.filas_pc = max(lab.filas_pc or 0, (total + cols - 1) // cols)
        lab.cols_pc = max(lab.cols_pc or 0, cols)
        db.commit()
        print(f"lab {lab_id}: {creadas} creadas, {total} en total, grilla {lab.filas_pc}x{lab.cols_pc}")


if __name__ == "__main__":
    main()
