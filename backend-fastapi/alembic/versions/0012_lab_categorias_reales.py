"""lab categorias reales: add Descripcion + replace 4 generic seeds with 9 real ones.

Revision ID: 0012_lab_categorias_reales
Revises: 0011_laboratorios
Create Date: 2026-10-01
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision: str = "0012_lab_categorias_reales"
down_revision: str | None = "0011_laboratorios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENERICS = (
    "Mantenimiento preventivo",
    "Mantenimiento correctivo",
    "Calibración",
    "Otros",
)

# Exact names + guide cases from staff catalog.
CATEGORIAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "HARDWARE",
        (
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
    ),
    (
        "RED E INTERNET",
        (
            "Sin conexión a Internet",
            "Conexión lenta",
            "Problemas de conectividad",
            "Filtros Wi-Fi (FortiGate)",
            "Verificación de conexiones",
            "Reporte de fallas de conectividad",
            "Cierre de laboratorios",
        ),
    ),
    (
        "INFRAESTRUCTURA",
        (
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
    ),
    (
        "SOFTWARE",
        (
            "Instalación de programas",
            "Actualización de programas",
            "Errores de Windows",
            "Drivers",
            "Reinstalación de software",
            "Configuración de programas y licencias",
        ),
    ),
    (
        "SOPORTE ACADÉMICO",
        (
            "Asistencia al docente",
            "Asistencia al estudiante",
            "Apoyo durante prácticas",
            "Preparación de equipos para clases",
            "Solicitudes de funcionamiento",
        ),
    ),
    (
        "SEGURIDAD",
        (
            "Virus o malware",
            "Uso indebido de equipos",
            "Accesos no autorizados",
            "Normas de uso",
            "Incidentes de seguridad",
        ),
    ),
    (
        "INVENTARIO",
        (
            "Equipos dañados",
            "Equipos faltantes",
            "Cambios de equipo",
            "Reubicación",
            "Objetos perdidos/encontrados",
            "Control de inventario",
        ),
    ),
    (
        "SOPORTE EN LABORATORIOS",
        (
            "Mamparas de robótica",
            "Vitrinas de resguardo",
            "Llaves de robótica",
            "Resguardo temporal de piezas",
            "Objetos bajo custodia",
            "Piezas faltantes en robótica",
        ),
    ),
    (
        "REPORTE Y GESTIÓN",
        (
            "Fallas en impresoras/proyectores",
            "Equipos para revisión técnica",
            "Seguimiento de incidencias",
            "Solicitudes de reparación",
            "Necesidades de software",
            "Reportes por laboratorio",
        ),
    ),
)


def _guia(casos: tuple[str, ...]) -> str:
    return ", ".join(casos)


def upgrade() -> None:
    op.add_column("LabCategorias", sa.Column("Descripcion", sa.String(2000), nullable=True))
    conn = op.get_bind()
    # Drop the 4 generic seeds only when exactly matching (FK-safe: no atenciones reference them yet).
    conn.execute(
        text("DELETE FROM \"LabCategorias\" WHERE \"Nombre\" IN :nombres").bindparams(
            sa.bindparam("nombres", expanding=True)
        ),
        {"nombres": list(GENERICS)},
    )
    ahora = datetime.now(UTC)
    for nombre, casos in CATEGORIAS:
        guia = _guia(casos)
        row = conn.execute(
            text("SELECT \"Id\" FROM \"LabCategorias\" WHERE \"Nombre\" = :n"),
            {"n": nombre},
        ).first()
        if row is None:
            conn.execute(
                text(
                    "INSERT INTO \"LabCategorias\" "
                    "(\"Nombre\", \"Descripcion\", \"Activa\", \"CreatedAt\") "
                    "VALUES (:n, :d, TRUE, :ahora)"
                ),
                {"n": nombre, "d": guia, "ahora": ahora},
            )
        else:
            conn.execute(
                text(
                    "UPDATE \"LabCategorias\" SET \"Descripcion\" = :d, \"Activa\" = TRUE "
                    "WHERE \"Nombre\" = :n"
                ),
                {"n": nombre, "d": guia},
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM \"LabCategorias\" WHERE \"Nombre\" IN :nombres").bindparams(
            sa.bindparam("nombres", expanding=True)
        ),
        {"nombres": [nombre for nombre, _ in CATEGORIAS]},
    )
    op.drop_column("LabCategorias", "Descripcion")
    ahora = datetime.now(UTC)
    conn.execute(
        sa.table(
            "LabCategorias",
            sa.column("Nombre", sa.String(200)),
            sa.column("Activa", sa.Boolean()),
            sa.column("CreatedAt", sa.DateTime(timezone=True)),
        ).insert(),
        [{"Nombre": n, "Activa": True, "CreatedAt": ahora} for n in GENERICS],
    )
