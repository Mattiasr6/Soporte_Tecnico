"""Siembra inventario desde el Excel de computo: ficha por lab, catalogo de
software, relaciones lab-software y estados iniciales por PC.

Uso (dentro del container api):
  DATABASE_URL=... python scripts/seed_software.py [--solo=lab,software,relaciones,estados]

Idempotente por nombre normalizado: no duplica, solo completa lo que falta.
Requiere .env con DATABASE_URL. Nunca toca Atenciones existentes.
"""

import os
import re
import sys
import unicodedata
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import load_workbook

from app.db.base import SessionLocal
from app.models.lab_pc import LabPc
from app.models.laboratorio import Laboratorio
from app.models.software import PcSoftware, Software, SoftwareLab

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XLSX = os.environ.get(
    "SOFTWARE_XLSX",
    os.path.join(RAIZ, "docs", "csv", "Cantidad y programas en Laboratorios de Computo UPDS-SCZ.xlsx"),
)

ALIAS = {
    "zinaji": "zinjai",
    "google chorme": "google chrome",
    "fire fox": "firefox",
    "mintab 19": "minitab",
    "ibms sps": "ibm spss",
    "ibms spss statics 23": "ibm spss",
    "ibms spss 21": "ibm spss",
    "ibm spss statics 21": "ibm spss",
    "mysql server": "mysql",
    "mysql ": "mysql",
    "my sql": "mysql",
    "vwware vix": "vmware vix",
    "vmware workstation": "vmware",
    "illustrator": "adobe illustrator",
    "delfin": "delfinet",
    "logisim-evolution": "logisim evolution",
    "ibm spss statistcs 21": "ibm spss",
    "llicencia gratuita": "x",
}

DISPLAY = {
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "zinjai": "Zinjai",
    "ibm spss": "IBM SPSS",
    "minitab": "Minitab",
    "mysql": "MySQL",
    "vmware vix": "VMware VIX",
    "vmware": "VMware",
    "delfinet": "DelfiNET",
    "logisim evolution": "Logisim Evolution",
    "adobe illustrator": "Adobe Illustrator",
}


def norm(s: object) -> str:
    t = unicodedata.normalize("NFD", str(s or "").strip().casefold())
    t = re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn"))
    return ALIAS.get(t, t)


def norm_lic(s: object) -> str:
    t = norm(s)
    if "/" in t:
        return "mixta"
    if "crack" in t:
        return "crackeado"
    if "educat" in t:
        return "educativa"
    return "gratuita"


def labs_por_lista(s: object) -> set[int] | None:
    """'TODOS' -> None (todos); '3, 4, 5' -> {3,4,5}; 'PC DOCENTES' -> set() + marca."""
    t = str(s or "").strip()
    if t.upper() == "TODOS":
        return None
    nums = {int(x) for x in re.findall(r"\d+", t)}
    return {n for n in nums if 1 <= n <= 10}


def main() -> None:
    solo = set()
    for a in sys.argv[1:]:
        if a.startswith("--solo="):
            solo = set(a.split("=", 1)[1].split(","))
    wb = load_workbook(XLSX, read_only=True, data_only=True)
    ahora = datetime.now(UTC)
    with SessionLocal() as db:
        por_codigo = {
            lab.codigo: lab
            for lab in db.query(Laboratorio).all()
            if lab.codigo.startswith("LAB-")
        }

        # 1. ficha tecnica + capacidad
        if not solo or "lab" in solo:
            det = wb["Detalle tec. PC"]
            for fila in det.iter_rows(min_row=3, max_row=12, values_only=True):
                if not fila[1]:
                    continue
                m = re.search(r"(\d+)", str(fila[1]))
                if not m:
                    continue
                lab = por_codigo.get(f"LAB-{int(m.group(1)):02d}")
                if lab is None:
                    continue
                lab.procesador = str(fila[3] or "")[:200] or None
                lab.ram = str(fila[4] or "")[:100] or None
                lab.disco = str(fila[5] or "")[:100] or None
                lab.marca = str(fila[6] or "")[:100] or None
                lab.gpu = None if str(fila[7] or "").strip().lower() == "no" else str(fila[7])[:100]
                lab.monitores = str(fila[8] or "")[:100] or None
            cap = wb["Capacidad Labs Computo"]
            for fila in cap.iter_rows(values_only=True):
                if not fila[0] or not str(fila[0]).strip().isdigit():
                    continue
                lab = por_codigo.get(f"LAB-{int(fila[0]):02d}")
                if lab is None:
                    continue
                try:
                    lab.pcs_estudiantes = int(fila[1])
                    lab.pcs_docentes = int(fila[2])
                    lab.sillas = int(fila[5])
                    lab.capacidad = int(fila[6])
                except (TypeError, ValueError):
                    pass
            db.commit()
            print("ficha tecnica: ok")

        # 2. catalogo desde Programas x Carrera
        catalogo: dict[str, dict] = {}

        def poner(nombre: object, lic: object = "", uso: object = "", labs=None, docentes=False):
            crudo = str(nombre or "").strip()
            if not crudo:
                return
            clave = norm(crudo)
            if not clave or clave == "x":
                return
            e = catalogo.setdefault(
                clave, {"nombre": DISPLAY.get(clave, crudo), "lic": "", "uso": "", "labs": set(), "docentes": False}
            )
            if lic and not e["lic"]:
                e["lic"] = norm_lic(lic)
            if uso and not e["uso"]:
                e["uso"] = str(uso)[:500]
            e["docentes"] = e["docentes"] or docentes
            if labs is None:
                e["labs"] = None
            elif e["labs"] is not None:
                e["labs"] |= set(labs)

        # catalogo siempre se puebla: lo usan "software" y "relaciones"
        xc = wb["Programas x Carrera"]
        for fila in xc.iter_rows(min_row=3, values_only=True):
            if not fila[1]:
                continue
            labs = labs_por_lista(fila[4])
            poner(
                fila[1], fila[2], fila[3], labs,
                docentes="DOCENTE" in str(fila[4] or "").upper(),
            )
        prog = wb["Programas"]
        for fila in prog.iter_rows(min_row=5, values_only=True):
            for base in range(1, 31, 3):
                nombre = fila[base] if base < len(fila) else None
                lic = fila[base + 1] if base + 1 < len(fila) else ""
                if nombre and str(nombre).strip():
                    poner(nombre, lic, labs={base // 3 + 1})
        creados = 0
        if not solo or "software" in solo:
            for _clave, e in sorted(catalogo.items()):
                existe = (
                    db.query(Software).filter(Software.nombre == e["nombre"]).first()
                )
                if existe is None:
                    db.add(
                        Software(
                            nombre=e["nombre"],
                            licencia=e["lic"] or "gratuita",
                            uso=e["uso"],
                            esencial=e["labs"] is None,
                            docentes=e["docentes"],
                            activo=True,
                            created_at=ahora,
                        )
                    )
                    creados += 1
            db.commit()
            print(f"software: {creados} nuevos, {len(catalogo)} en Excel")

        # 3. relaciones lab-software
        if not solo or "relaciones" in solo:
            por_norm = {norm(s.nombre): s for s in db.query(Software).all()}
            nuevas = 0
            for clave, e in catalogo.items():
                sw = por_norm.get(clave)
                if sw is None:
                    continue
                labs = e["labs"] if e["labs"] is not None else set(range(1, 11))
                for n in labs:
                    lab = por_codigo.get(f"LAB-{n:02d}")
                    if lab is None:
                        continue
                    existe = (
                        db.query(SoftwareLab)
                        .filter(
                            SoftwareLab.software_id == sw.id,
                            SoftwareLab.laboratorio_id == lab.id,
                        )
                        .first()
                    )
                    if existe is None:
                        db.add(
                            SoftwareLab(
                                software_id=sw.id,
                                laboratorio_id=lab.id,
                                created_at=ahora,
                            )
                        )
                        nuevas += 1
            db.commit()
            print(f"relaciones: {nuevas} nuevas")

        # 4. estados iniciales por PC (instalado donde el lab lo tiene)
        if not solo or "estados" in solo:
            rels = db.query(SoftwareLab).all()
            por_lab: dict[int, list[int]] = {}
            for r in rels:
                por_lab.setdefault(r.laboratorio_id, []).append(r.software_id)
            nuevos = 0
            for lab_id, sw_ids in por_lab.items():
                pcs = db.query(LabPc).filter(LabPc.laboratorio_id == lab_id).all()
                hay = {
                    (r.pc_id, r.software_id)
                    for r in db.query(PcSoftware)
                    .filter(PcSoftware.pc_id.in_([p.id for p in pcs] or [-1]))
                    .all()
                }
                for p in pcs:
                    for sw_id in sw_ids:
                        if (p.id, sw_id) not in hay:
                            db.add(
                                PcSoftware(
                                    pc_id=p.id,
                                    software_id=sw_id,
                                    estado="instalado",
                                    created_at=ahora,
                                    updated_at=ahora,
                                )
                            )
                            nuevos += 1
            db.commit()
            print(f"estados: {nuevos} nuevos")


if __name__ == "__main__":
    main()
