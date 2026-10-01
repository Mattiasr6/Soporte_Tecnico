"""Idempotent seed for laboratorios service: 10 labs + 9 real categories.

Usage from backend-fastapi/:  python scripts/seed_laboratorios.py
Requires .env with DATABASE_URL. Requires migration 0012 applied.
Never deletes; upserts by codigo (labs) and normalized nombre (categories),
so re-running is safe. Writes to whichever DB DATABASE_URL points to —
double-check it before running (never run against production by accident).
"""

import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.models.laboratorio import LabCategoria, Laboratorio

LABORATORIOS = [(f"LAB-{i:02d}", f"TBD-{i:02d}") for i in range(1, 11)]
# Exact names + guide cases from the staff catalog; guia is comma-joined cases.
CATEGORIAS: dict[str, tuple[str, ...]] = {
    "HARDWARE": (
        "Equipo no enciende",
        "Monitor sin señal",
        "Teclado dañado",
        "Mouse dañado",
        "Cambio de pantalla por falla o daño del componente",
        "Mantenimiento preventivo de equipos informáticos",
        "Mantenimiento correctivo de equipos informáticos",
        "Reemplazo de componentes internos (RAM, disco, fuente y otros)",
        "Verificación y diagnóstico de fallas de hardware",
    ),
    "RED E INTERNET": (
        "Sin conexión a Internet",
        "Conexión lenta",
        "Problemas de conectividad",
        "Filtros Wi-Fi (FortiGate)",
        "Verificación de conexiones",
        "Reporte de fallas de conectividad",
        "Cierre de laboratorios",
    ),
    "INFRAESTRUCTURA": (
        "Problemas eléctricos",
        "Cableado dañado",
        "Mobiliario dañado",
        "Fallas de aire acondicionado",
        "Limpieza y mantenimiento del área",
        "Apertura de laboratorios",
        "Cierre de laboratorios",
        "Resguardo de llaves y controles",
        "Daños o anomalías",
    ),
    "SOFTWARE": (
        "Instalación de programas",
        "Actualización de programas",
        "Errores de Windows",
        "Drivers",
        "Reinstalación de software",
        "Configuración de programas y licencias",
    ),
    "SOPORTE ACADÉMICO": (
        "Asistencia al docente",
        "Asistencia al estudiante",
        "Apoyo durante prácticas",
        "Preparación de equipos para clases",
        "Solicitudes de funcionamiento",
    ),
    "SEGURIDAD": (
        "Virus o malware",
        "Uso indebido de equipos",
        "Accesos no autorizados",
        "Normas de uso",
        "Incidentes de seguridad",
    ),
    "INVENTARIO": (
        "Equipos dañados",
        "Equipos faltantes",
        "Cambios de equipo",
        "Reubicación",
        "Objetos perdidos/encontrados",
        "Control de inventario",
    ),
    "SOPORTE EN LABORATORIOS": (
        "Mamparas de robótica",
        "Vitrinas de resguardo",
        "Llaves de robótica",
        "Resguardo temporal de piezas",
        "Objetos bajo custodia",
        "Piezas faltantes en robótica",
    ),
    "REPORTE Y GESTIÓN": (
        "Fallas en impresoras/proyectores",
        "Equipos para revisión técnica",
        "Seguimiento de incidencias",
        "Solicitudes de reparación",
        "Necesidades de software",
        "Reportes por laboratorio",
    ),
}


def main() -> None:
    ahora = datetime.now(UTC)
    with SessionLocal() as db:
        for codigo, nombre in LABORATORIOS:
            lab = db.scalar(select(Laboratorio).where(Laboratorio.codigo == codigo))
            if lab is None:
                db.add(
                    Laboratorio(
                        codigo=codigo, nombre=nombre, activa=True, created_at=ahora
                    )
                )
            elif not lab.activa or lab.nombre != nombre:
                lab.nombre = nombre
                lab.activa = True
        existentes = {
            (c.nombre or "").strip().lower(): c
            for c in db.scalars(select(LabCategoria)).all()
        }
        for nombre, casos in CATEGORIAS.items():
            guia = ", ".join(casos)
            cat = existentes.get(nombre.strip().lower())
            if cat is None:
                db.add(
                    LabCategoria(
                        nombre=nombre,
                        descripcion=guia,
                        activa=True,
                        created_at=ahora,
                    )
                )
            else:
                if not cat.activa:
                    cat.activa = True
                if cat.descripcion != guia:
                    cat.descripcion = guia
        db.commit()
    print(f"OK: {len(LABORATORIOS)} laboratorios, {len(CATEGORIAS)} categorias.")


if __name__ == "__main__":
    main()
