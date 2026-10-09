"""Siembra las salas desde el PDF de etiquetado (geometría) + Excel (cantidades).

Por lab: filas, ancla de pasillo, esquina del docente, base SCPC y cantidad.
Dibuja la grilla, reserva la esquina del docente y rellena el resto en orden.
Idempotente por reemplazo: borra las PCs del lab y las recrea (solo dev).
"""
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.db.session import SessionLocal
from app.models.lab_pc import LabPc
from app.models.laboratorio import Laboratorio

# lab_id: (filas, cols_totales, col_pasillo, celda_docente, base_scpc, cant_scpc)
LAYOUTS = {
    1: (5, 7, 2, (0, 6), 100, 20),
    2: (6, 9, 4, (0, 0), 200, 30),
    3: (4, 8, 4, (0, 0), 300, 20),
    4: (3, 9, 4, (0, 8), 400, 12),
    5: (5, 9, 4, (0, 8), 500, 20),
    6: (5, 9, 4, (4, 8), 600, 25),
    7: (5, 8, 3, (0, 7), 700, 25),
    8: (5, 9, 4, (0, 0), 800, 25),
    9: (5, 10, 5, (0, 0), 900, 30),
    10: (5, 11, 5, (0, 10), 1000, 30),
}


def main() -> None:
    solo = [int(a) for a in sys.argv[1:]] or sorted(LAYOUTS)
    with SessionLocal() as db:
        for lab_id in solo:
            filas, cols, pasillo, docente, base, cant = LAYOUTS[lab_id]
            lab = db.get(Laboratorio, lab_id)
            assert lab is not None, f"lab {lab_id} no existe"
            db.query(LabPc).filter(LabPc.laboratorio_id == lab_id).delete()
            ahora = datetime.now(UTC)
            # docente en su esquina
            db.add(
                LabPc(
                    laboratorio_id=lab_id, nombre="DOCENTE",
                    fila=docente[0], col=docente[1], activa=True, created_at=ahora,
                )
            )
            creadas = 0
            i = 1
            for f in range(filas):
                for c in range(cols):
                    if creadas >= cant:
                        break
                    if c == pasillo or (f, c) == docente:
                        continue
                    db.add(
                        LabPc(
                            laboratorio_id=lab_id, nombre=f"SCPC {base + i}",
                            fila=f, col=c, activa=True, created_at=ahora,
                        )
                    )
                    creadas += 1
                    i += 1
                if creadas >= cant:
                    break
            assert creadas == cant, f"lab {lab_id}: solo entraron {creadas}/{cant}"
            lab.filas_pc, lab.cols_pc = filas, cols
            db.commit()
            print(f"lab {lab_id}: {creadas} SCPC + DOCENTE en grilla {filas}x{cols}")


if __name__ == "__main__":
    main()
