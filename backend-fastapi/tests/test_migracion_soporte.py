"""Cutover data move: old Soporte lab tables + auxiliar JSON → horarios.

Every test runs inside one transaction that is rolled back, so the seeded
source rows, perfiles and whatever the migration writes never stay in the
test DB. The auxiliar JSON files are written to a temp dir per test.
"""

import csv
import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, text

from app.db.base import engine
from app.services.migracion_soporte import (
    LA_PAZ,
    Resultado,
    escribir_reporte,
    migrar,
)

CREADO = datetime(2026, 10, 6, 13, 15, tzinfo=UTC)  # 09:15 in La Paz (turno M)


def _sabado_lejano() -> date:
    dia = date(2030, 10, 7)
    return dia + timedelta(days=(5 - dia.weekday()) % 7)


SABADO = _sabado_lejano()


@pytest.fixture
def conn() -> Iterator[Connection]:
    with engine.connect() as c:
        tx = c.begin()
        try:
            yield c
        finally:
            tx.rollback()


def _uno(c: Connection, sql: str, /, **p: Any) -> Any:
    return c.execute(text(sql), p).scalar_one()


def _categoria(c: Connection, nombre: str) -> int:
    existente = c.execute(
        text('select "Id" from "LabCategorias" where "Nombre" = :n'), {"n": nombre}
    ).scalar()
    if existente is not None:
        return int(existente)
    return int(
        _uno(
            c,
            'insert into "LabCategorias" ("Nombre","Activa","CreatedAt") '
            'values (:n, true, now()) returning "Id"',
            n=nombre,
        )
    )


def _laboratorio(c: Connection, codigo: str) -> int:
    return int(
        _uno(
            c,
            'insert into "Laboratorios" ("Codigo","Nombre","Activa","FilasPc","ColsPc",'
            '"CreatedAt") values (:c, :c, true, 0, 0, now()) returning "Id"',
            c=codigo,
        )
    )


def _atencion(c: Connection, lab: int, cat: int, **campos: Any) -> int:
    valores: dict[str, Any] = {
        "usuario": _uno(c, 'select min("Id") from "Usuarios"'),
        "lab": lab,
        "cat": cat,
        "aux": "Zeta Migracion Uno",
        "pc": None,
        "desc": "Instalación de Office",
        "sol": "Instalado y probado",
        "obs": None,
        "turno": "mañana",
        "medio": "Presencial",
        "fecha": CREADO.date(),
        "creado": CREADO,
    }
    valores.update(campos)
    return int(
        _uno(
            c,
            'insert into "LabAtenciones" ("UsuarioId","LaboratorioId","CategoriaId",'
            '"AuxiliarNombre","PcNombre","Descripcion","Solucion","Observaciones",'
            '"FueraDeTurno","Turno","MedioSolicitud","FechaRegistro","CreatedAt") values '
            "(:usuario, :lab, :cat, :aux, :pc, :desc, :sol, :obs, false, :turno, :medio, "
            ':fecha, :creado) returning "Id"',
            **valores,
        )
    )


def _perfil(c: Connection, nombre: str, correo: str, rol: str = "auxiliar") -> str:
    return str(
        _uno(
            c,
            "insert into horarios.perfiles (nombre_completo, correo, rol) "
            "values (:n, :c, :r) returning id",
            n=nombre,
            c=correo,
            r=rol,
        )
    )


@pytest.fixture
def fuente(conn: Connection, tmp_path: Path) -> dict[str, Any]:
    """Seed one matched lab, one lab without ambiente, two PCs, two perfiles
    and four lab attentions, plus the three auxiliar JSON files."""
    amb = int(
        _uno(
            conn,
            "insert into horarios.ambientes (codigo, nombre) "
            "values ('ZMIG-01', 'Lab migración') returning id",
        )
    )
    pc_ok = int(
        _uno(
            conn,
            "insert into horarios.ambiente_pcs (ambiente_id, etiqueta) "
            "values (:a, 'ZPC-01') returning id",
            a=amb,
        )
    )
    _uno(
        conn,
        "insert into horarios.ambiente_pcs (ambiente_id, etiqueta, estado) "
        "values (:a, 'ZPC-02', 'mantenimiento') returning id",
        a=amb,
    )
    uno = _perfil(conn, "Zeta Migración Uno", "zeta.uno@prueba.upds.edu.bo")
    dos = _perfil(conn, "Zeta Migracion Dos", "zeta.dos@prueba.upds.edu.bo")
    lab = _laboratorio(conn, "ZMIG-01")
    lab_sin = _laboratorio(conn, "ZMIG-99")
    software = _categoria(conn, "SOFTWARE")
    ids = {
        "emparejada": _atencion(
            conn,
            lab,
            software,
            aux="Zeta Migracion Uno + zeta migracion dos",
            pc="zpc-01",
            medio="WhatsApp",
            obs="Pidió también el antivirus",
        ),
        "pc_y_aux": _atencion(
            conn, lab, software, aux="Fantasma Sin Cuenta", pc="ZPC-77", turno=""
        ),
        "sin_lab": _atencion(conn, lab_sin, software, turno="noche"),
        "pc_mant": _atencion(conn, lab, software, pc="ZPC-02", turno="tarde"),
    }
    (tmp_path / "equipo_auxiliares.json").write_text(
        json.dumps(
            {
                "auxiliares": [
                    {"nombre": "Zeta Migracion Uno", "activo": True, "encargado": True},
                    {
                        "nombre": "Fantasma Sin Cuenta",
                        "activo": True,
                        "encargado": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "horarios_auxiliares.json").write_text(
        json.dumps(
            {
                "mañana": {
                    "auxiliares": ["Zeta Migracion Uno", "Fantasma Sin Cuenta"],
                    "inicio": "07:00",
                    "fin": "12:00",
                },
                "mediodia": {
                    "auxiliares": ["Zeta Migracion Dos"],
                    "inicio": "12:00",
                    "fin": "16:00",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "horarios_sabados.json").write_text(
        json.dumps(
            {
                SABADO.isoformat(): {
                    "mañana": {
                        "auxiliares": ["Zeta Migracion Uno", "Fantasma Sin Cuenta"],
                        "inicio": "08:00",
                        "fin": "12:00",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return {
        "ids": ids,
        "uno": uno,
        "dos": dos,
        "amb": amb,
        "pc_ok": pc_ok,
        "dir": tmp_path,
    }


def _migrada(conn: Connection, origen_id: int) -> dict[str, Any]:
    fila = (
        conn.execute(
            text(
                "select a.* from horarios.atenciones a join horarios.migracion_origen m "
                "on m.destino_id = a.id::text where m.origen = 'LabAtenciones' "
                "and m.origen_id = :o"
            ),
            {"o": str(origen_id)},
        )
        .mappings()
        .one()
    )
    return dict(fila)


def _motivos(res: Resultado, origen_id: int | str) -> set[str]:
    return {i.motivo for i in res.incidencias if i.origen_id == str(origen_id)}


def _conteo(conn: Connection, tabla: str) -> int:
    return int(_uno(conn, f"select count(*) from {tabla}"))


def test_dry_run_no_escribe_nada(conn: Connection, fuente: dict[str, Any]) -> None:
    tablas = (
        "horarios.atenciones",
        "horarios.migracion_origen",
        "horarios.sabados",
        "horarios.rotacion_sabados",
    )
    antes = {t: _conteo(conn, t) for t in tablas}

    res = migrar(conn, data_dir=fuente["dir"], aplicar=False)

    assert {t: _conteo(conn, t) for t in tablas} == antes
    perfil = conn.execute(
        text("select rol, turno_habitual from horarios.perfiles where id = :i"),
        {"i": fuente["uno"]},
    ).one()
    assert (perfil.rol, perfil.turno_habitual) == ("auxiliar", None)
    assert res.conteos["atenciones_nuevas"] == 4
    assert res.conteos["sabados_nuevos"] == 1
    assert _motivos(res, fuente["ids"]["pc_y_aux"]) >= {
        "pc_sin_match",
        "auxiliar_sin_perfil",
    }


def test_atencion_emparejada(conn: Connection, fuente: dict[str, Any]) -> None:
    migrar(conn, data_dir=fuente["dir"], aplicar=True)

    a = _migrada(conn, fuente["ids"]["emparejada"])
    assert a["ambiente_id"] == fuente["amb"]
    assert a["pc_id"] == fuente["pc_ok"]
    assert str(a["auxiliar_id"]) == fuente["uno"]
    assert [str(x) for x in a["colaboradores"]] == [fuente["dos"]]
    assert a["tipo"] == "programas"
    assert (a["turno"], a["medio_solicitud"]) == ("M", "WhatsApp")
    assert a["creado_en"] == CREADO
    assert a["estado"] == "resuelto"
    assert a["descripcion"] == "Instalación de Office"
    assert "antivirus" in a["solucion"]
    assert "[Migrado]" not in a["descripcion"]
    assert a["detalles"]["migracion"]["categoria"] == "SOFTWARE"


def test_pc_y_auxiliar_sin_match(conn: Connection, fuente: dict[str, Any]) -> None:
    res = migrar(conn, data_dir=fuente["dir"], aplicar=True)

    origen = fuente["ids"]["pc_y_aux"]
    a = _migrada(conn, origen)
    assert a["pc_id"] is None
    assert a["auxiliar_id"] is None
    assert a["ambiente_id"] == fuente["amb"]
    assert "[Migrado] PC: ZPC-77 · Auxiliar: Fantasma Sin Cuenta" in a["descripcion"]
    # Empty source turno: the insert trigger derives it from creado_en (09:15 → M).
    assert a["turno"] == "M"
    assert _motivos(res, origen) >= {"pc_sin_match", "auxiliar_sin_perfil"}


def test_lab_sin_ambiente_y_pc_no_operativa(
    conn: Connection, fuente: dict[str, Any]
) -> None:
    res = migrar(conn, data_dir=fuente["dir"], aplicar=True)

    sin_lab = _migrada(conn, fuente["ids"]["sin_lab"])
    assert sin_lab["ambiente_id"] is None
    assert sin_lab["turno"] == "N"
    assert "Lab: ZMIG-99" in sin_lab["descripcion"]
    assert "laboratorio_sin_ambiente" in _motivos(res, fuente["ids"]["sin_lab"])

    mant = _migrada(conn, fuente["ids"]["pc_mant"])
    assert mant["pc_id"] is None
    assert mant["turno"] == "T"
    assert "PC: ZPC-02" in mant["descripcion"]
    assert "pc_no_operativa" in _motivos(res, fuente["ids"]["pc_mant"])


def test_perfiles_turnos_y_sabados(conn: Connection, fuente: dict[str, Any]) -> None:
    res = migrar(conn, data_dir=fuente["dir"], aplicar=True)

    uno = conn.execute(
        text("select rol, turno_habitual from horarios.perfiles where id = :i"),
        {"i": fuente["uno"]},
    ).one()
    assert (uno.rol, uno.turno_habitual) == ("encargado", "M")
    dos = _uno(
        conn,
        "select turno_habitual from horarios.perfiles where id = :i",
        i=fuente["dos"],
    )
    assert dos == "MD"
    nota = _uno(conn, "select nota from horarios.sabados where fecha = :f", f=SABADO)
    assert "Fantasma Sin Cuenta" in nota
    horas = conn.execute(
        text(
            "select turno, hora_inicio::text, hora_fin::text from "
            "horarios.sabado_horarios where fecha = :f"
        ),
        {"f": SABADO},
    ).all()
    assert [tuple(h) for h in horas] == [("M", "08:00:00", "12:00:00")]
    asignados = conn.execute(
        text(
            "select auxiliar_id::text, turno from horarios.rotacion_sabados "
            "where fecha = :f"
        ),
        {"f": SABADO},
    ).all()
    assert [tuple(x) for x in asignados] == [(fuente["uno"], "M")]
    sin_perfil = {
        i.seccion for i in res.incidencias if i.detalle == "Fantasma Sin Cuenta"
    }
    assert sin_perfil == {"atenciones", "equipo", "turnos", "sabados"}


def test_segunda_corrida_no_duplica(conn: Connection, fuente: dict[str, Any]) -> None:
    migrar(conn, data_dir=fuente["dir"], aplicar=True)
    tablas = (
        "horarios.atenciones",
        "horarios.migracion_origen",
        "horarios.sabados",
        "horarios.sabado_horarios",
        "horarios.rotacion_sabados",
    )
    despues_primera = {t: _conteo(conn, t) for t in tablas}

    res = migrar(conn, data_dir=fuente["dir"], aplicar=True)

    assert {t: _conteo(conn, t) for t in tablas} == despues_primera
    assert res.conteos["atenciones_nuevas"] == 0
    assert res.conteos["atenciones_ya_migradas"] == 4
    assert res.conteos["sabados_nuevos"] == 0
    assert res.conteos["perfiles_actualizados"] == 0


def test_reporte_csv_y_json(
    conn: Connection, fuente: dict[str, Any], tmp_path: Path
) -> None:
    res = migrar(conn, data_dir=fuente["dir"], aplicar=False)
    origen = str(fuente["ids"]["pc_y_aux"])

    ruta_csv = escribir_reporte(res, tmp_path / "reporte.csv")
    with ruta_csv.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert set(filas[0]) == {"seccion", "origen_id", "motivo", "detalle"}
    assert {"atenciones", origen, "pc_sin_match", "ZPC-77"} <= {
        v for fila in filas if fila["origen_id"] == origen for v in fila.values()
    }

    ruta_json = escribir_reporte(res, tmp_path / "reporte.json")
    datos = json.loads(ruta_json.read_text(encoding="utf-8"))
    assert datos["conteos"]["atenciones_nuevas"] == 4
    assert {
        "seccion": "atenciones",
        "origen_id": origen,
        "motivo": "auxiliar_sin_perfil",
        "detalle": "Fantasma Sin Cuenta",
    } in datos["incidencias"]


def test_segunda_corrida_completa_perfiles_creados_despues(
    conn: Connection, fuente: dict[str, Any]
) -> None:
    migrar(conn, data_dir=fuente["dir"], aplicar=True)
    origen = fuente["ids"]["pc_y_aux"]
    assert _migrada(conn, origen)["auxiliar_id"] is None
    fantasma = _perfil(conn, "Fantasma Sin Cuenta", "fantasma@prueba.upds.edu.bo")

    res = migrar(conn, data_dir=fuente["dir"], aplicar=True)

    a = _migrada(conn, origen)
    assert str(a["auxiliar_id"]) == fantasma
    assert str(a["resuelto_por"]) == fantasma
    # The original names stay in the text: it is the migrated record.
    assert "Auxiliar: Fantasma Sin Cuenta" in a["descripcion"]
    assert res.conteos["atenciones_auxiliar_completado"] == 1
    assert res.conteos["atenciones_nuevas"] == 0
    asignados = conn.execute(
        text(
            "select auxiliar_id::text, turno from horarios.rotacion_sabados "
            "where fecha = :f order by turno, auxiliar_id"
        ),
        {"f": SABADO},
    ).all()
    assert sorted(tuple(x) for x in asignados) == sorted(
        [(fuente["uno"], "M"), (fantasma, "M")]
    )
    assert res.conteos["sabados_nuevos"] == 0


def test_fecha_registro_manda_sobre_created_at(
    conn: Connection, fuente: dict[str, Any]
) -> None:
    lab = _uno(conn, """select "Id" from "Laboratorios" where "Codigo" = 'ZMIG-01'""")
    cat = _categoria(conn, "SOFTWARE")
    # Typed in the next afternoon for the previous day's mediodía.
    tardia = _atencion(
        conn,
        lab,
        cat,
        turno="mediodia",
        fecha=date(2026, 10, 6),
        creado=datetime(2026, 10, 7, 19, 33, tzinfo=UTC),
    )
    # 22:04 in La Paz, stamped by Django with the UTC date: the time is real.
    noche = datetime(2026, 10, 7, 2, 4, tzinfo=UTC)
    nocturna = _atencion(
        conn, lab, cat, turno="noche", fecha=date(2026, 10, 7), creado=noche
    )
    inicio_md = _uno(
        conn, "select hora_inicio from horarios.horarios_turno where turno = 'MD'"
    )

    res = migrar(conn, data_dir=fuente["dir"], aplicar=True)

    a = _migrada(conn, tardia)
    esperado = datetime.combine(date(2026, 10, 6), inicio_md, LA_PAZ)
    assert (a["creado_en"], a["turno"]) == (esperado, "MD")
    assert a["detalles"]["migracion"]["creado"].startswith("2026-10-07T19:33")
    assert "hora_ajustada_a_fecha_registro" in _motivos(res, tardia)
    assert _migrada(conn, nocturna)["creado_en"] == noche
    assert _motivos(res, nocturna) == set()
