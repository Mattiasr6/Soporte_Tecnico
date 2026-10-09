"""Schema `horarios` (ported ASIGNACION data model, migration 0021).

Every test runs inside a transaction that is rolled back, so nothing it creates
stays in the database. The anti-clash triggers are DEFERRABLE INITIALLY
DEFERRED (they fire at commit), so the tests force them with
SET CONSTRAINTS ALL IMMEDIATE instead of committing.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from app.db.base import engine

KEY_TABLES = (
    "perfiles",
    "ambientes",
    "ambiente_pcs",
    "asignaciones",
    "asignacion_horarios",
    "asignacion_fechas",
    "cesiones",
    "reservas",
    "reubicaciones",
    "bloques_horario",
    "horarios_turno",
    "sistemas_academicos",
    "tipos_reserva",
    "reportes_turno",
    "objetos_perdidos",
)


@pytest.fixture
def conn() -> Iterator[Connection]:
    with engine.connect() as c:
        tx = c.begin()
        try:
            yield c
        finally:
            tx.rollback()


def _scalar(conn: Connection, sql: str, **params: object) -> object:
    return conn.execute(text(sql), params).scalar_one()


def test_schema_and_key_tables_exist(conn: Connection) -> None:
    rows = conn.execute(
        text(
            "select table_name from information_schema.tables "
            "where table_schema = 'horarios'"
        )
    ).scalars()
    missing = set(KEY_TABLES) - set(rows)
    assert not missing


def test_catalog_seed_is_loaded(conn: Connection) -> None:
    for table in (
        "bloques_horario",
        "horarios_turno",
        "sistemas_academicos",
        "tipos_reserva",
    ):
        assert _scalar(conn, f"select count(*) from horarios.{table}") > 0, table


def test_no_supabase_leftovers(conn: Connection) -> None:
    policies = _scalar(
        conn, "select count(*) from pg_policies where schemaname = 'horarios'"
    )
    rls = _scalar(
        conn,
        "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'horarios' and c.relrowsecurity",
    )
    auth_refs = _scalar(
        conn,
        "select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
        "where n.nspname = 'horarios' and p.prosrc ~ '(auth|storage)\\.'",
    )
    assert (policies, rls, auth_refs) == (0, 0, 0)


def _new_asignacion(conn: Connection, docente: str, inicio: str, fin: str) -> int:
    ids = {
        "carrera": _scalar(
            conn,
            "insert into horarios.carreras (nombre) values (:n) returning id",
            n=f"Carrera test {docente}",
        ),
        "materia": _scalar(
            conn,
            "insert into horarios.materias (nombre) values (:n) returning id",
            n=f"Materia test {docente}",
        ),
        "docente": _scalar(
            conn,
            "insert into horarios.docentes (nombres, apellidos) values (:n, 'Test') returning id",
            n=docente,
        ),
        "sistema": _scalar(
            conn,
            "select id from horarios.sistemas_academicos where codigo = 'SEMESTRAL'",
        ),
        "ambiente": _scalar(
            conn, "select id from horarios.ambientes where codigo = 'LAB-01'"
        ),
    }
    asignacion = _scalar(
        conn,
        "insert into horarios.asignaciones "
        "(sistema_id, docente_id, materia_id, carrera_id, fecha_inicio, fecha_fin) "
        "values (:sistema, :docente, :materia, :carrera, '2031-03-03', '2031-03-28') "
        "returning id",
        **{k: v for k, v in ids.items() if k != "ambiente"},
    )
    conn.execute(
        text(
            "insert into horarios.asignacion_horarios "
            "(asignacion_id, dia_semana, hora_inicio, hora_fin, ambiente_id) "
            "values (:a, 1, :hi, :hf, :amb)"
        ),
        {"a": asignacion, "hi": inicio, "hf": fin, "amb": ids["ambiente"]},
    )
    return int(asignacion)


def test_non_overlapping_asignaciones_are_accepted(conn: Connection) -> None:
    _new_asignacion(conn, "Docente A", "07:00", "09:00")
    _new_asignacion(conn, "Docente B", "09:00", "11:00")
    conn.execute(text("set constraints all immediate"))


def test_overlapping_asignaciones_are_rejected(conn: Connection) -> None:
    _new_asignacion(conn, "Docente A", "07:00", "09:00")
    _new_asignacion(conn, "Docente B", "08:00", "10:00")
    with pytest.raises(DBAPIError) as err:
        conn.execute(text("set constraints all immediate"))
    assert err.value.orig.sqlstate == "P0001"


def _new_perfil(conn: Connection, rol: str = "admin") -> tuple[int, object]:
    usuario_id = _scalar(
        conn,
        'insert into public."Usuarios" ("Email", "DisplayName", "Role", "EstadoActual", '
        '"CanViewDashboard", "Activo", "TokenVersion", "CreatedAt", "UpdatedAt") '
        "values ('horarios.test@example.invalid', 'Horarios test', 'Jefe', 'Ausente', "
        'false, true, 0, now(), now()) returning "Id"',
    )
    perfil_id = _scalar(
        conn,
        "insert into horarios.perfiles (nombre_completo, correo, rol, usuario_id) "
        "values ('Perfil test', 'perfil.test@example.invalid', :rol, :u) returning id",
        u=usuario_id,
        rol=rol,
    )
    return int(usuario_id), perfil_id


def test_usuario_actual_is_null_without_setting(conn: Connection) -> None:
    _new_perfil(conn)
    assert _scalar(conn, "select horarios.fn_usuario_actual()") is None
    assert _scalar(conn, "select horarios.fn_rol_actual()") is None
    assert _scalar(conn, "select horarios.fn_puede_editar()") is False


def test_usuario_actual_ignores_non_numeric_setting(conn: Connection) -> None:
    _new_perfil(conn)
    conn.execute(text("select set_config('app.usuario_id', 'abc', true)"))
    assert _scalar(conn, "select horarios.fn_usuario_actual()") is None


def test_usuario_actual_follows_set_local(conn: Connection) -> None:
    usuario_id, perfil_id = _new_perfil(conn)
    conn.execute(
        text("select set_config('app.usuario_id', :u, true)"), {"u": str(usuario_id)}
    )
    assert _scalar(conn, "select horarios.fn_usuario_actual()") == perfil_id
    assert _scalar(conn, "select horarios.fn_rol_actual()") == "admin"
    assert _scalar(conn, "select horarios.fn_puede_editar()") is True
    asignacion = _new_asignacion(conn, "Docente C", "07:00", "09:00")
    creado_por = _scalar(
        conn, "select creado_por from horarios.asignaciones where id = :a", a=asignacion
    )
    assert creado_por == perfil_id


@pytest.mark.parametrize(
    ("helper", "expected"),
    [
        ("fn_puede_ver()", True),
        ("fn_puede_operar()", True),
        ("fn_puede_editar()", False),
        ("fn_puede_gestionar_auxiliares()", False),
        ("fn_es_admin()", False),
        ("fn_puede_cerrar_turno('M')", False),
    ],
)
def test_tecnico_operates_like_auxiliar_without_managing(
    conn: Connection, helper: str, expected: bool
) -> None:
    """0023: a Soporte Tecnico sees everything and operates, with no own shift."""
    usuario_id, _ = _new_perfil(conn, rol="tecnico")
    conn.execute(
        text("select set_config('app.usuario_id', :u, true)"), {"u": str(usuario_id)}
    )
    assert _scalar(conn, "select horarios.fn_rol_actual()") == "tecnico"
    assert _scalar(conn, f"select horarios.{helper}") is expected
