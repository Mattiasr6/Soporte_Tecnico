"""dia de la semana en los horarios

Revision ID: 0004_horario_dia
Revises: 0003_codigo_catalogo
Create Date: 2026-09-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_horario_dia"
down_revision: str | None = "0003_codigo_catalogo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("Horarios", sa.Column("DiaSemana", sa.Integer(), nullable=True))
    conexion = op.get_bind()
    ids = conexion.execute(sa.text('SELECT "Id" FROM "Horarios"')).fetchall()
    for (horario_id,) in ids:
        for dia in (2, 3, 4, 5):
            conexion.execute(
                sa.text(
                    'INSERT INTO "Horarios" ("UsuarioId", "Label", "HoraInicio1",'
                    ' "HoraFin1", "HoraInicio2", "HoraFin2", "Mes", "Anio",'
                    ' "CreatedAt", "DiaSemana")'
                    ' SELECT "UsuarioId", "Label", "HoraInicio1", "HoraFin1",'
                    ' "HoraInicio2", "HoraFin2", "Mes", "Anio", "CreatedAt", :dia'
                    ' FROM "Horarios" WHERE "Id" = :id'
                ),
                {"dia": dia, "id": horario_id},
            )
    conexion.execute(
        sa.text('UPDATE "Horarios" SET "DiaSemana" = 1 WHERE "DiaSemana" IS NULL')
    )
    op.alter_column("Horarios", "DiaSemana", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("Horarios_UsuarioId_Mes_Anio_key", "Horarios", type_="unique")
    op.create_unique_constraint(
        "uq_Horarios_usuario_mes_anio_dia",
        "Horarios",
        ["UsuarioId", "Mes", "Anio", "DiaSemana"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_Horarios_usuario_mes_anio_dia", "Horarios", type_="unique"
    )
    op.create_unique_constraint(
        "Horarios_UsuarioId_Mes_Anio_key", "Horarios", ["UsuarioId", "Mes", "Anio"]
    )
    conexion = op.get_bind()
    conexion.execute(sa.text('DELETE FROM "Horarios" WHERE "DiaSemana" > 1'))
    op.drop_column("Horarios", "DiaSemana")
