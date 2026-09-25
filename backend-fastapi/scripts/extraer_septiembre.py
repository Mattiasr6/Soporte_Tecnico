"""Extrae las atenciones desde prod y arma el CSV de carga.

Uso desde backend-fastapi/:
    python scripts/extraer_septiembre.py                      # desde 2026-09-01
    python scripts/extraer_septiembre.py 2026-01-01 historia.csv   # historia completa

Por que existe: el CSV es un snapshot y prod sigue recibiendo atenciones, asi que
un archivo "hecho a mano una vez" queda viejo enseguida (paso: 253 -> 274 en horas).
Este script se re-ejecuta en el momento de la carga.

Prod no tiene puerto mapeado al host, por eso se lee con `docker exec`.
Solo lectura: no escribe nada en prod.
"""

import csv
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.categorias import CATEGORIAS_VALIDAS
from app.services.csv_import import MEDIOS_VALIDOS, SOLICITANTES_VALIDOS

RAIZ = Path(__file__).resolve().parents[2]
MAPEO = RAIZ / "mapeo-areas.csv"
CATALOGO = RAIZ / "mapeo-areas-dedup.csv"
CONTENEDOR = "soporte-postgres"
DESDE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-01"
SALIDA = RAIZ / (sys.argv[2] if len(sys.argv) > 2 else "atenciones_septiembre.csv")

COLUMNAS = [
    "tecnico_email",
    "area_codigo",
    "colaborador_email",
    "medio_solicitud",
    "usuario_solicitante",
    "categoria",
    "descripcion",
    "solucion",
    "observaciones",
    "enlace_apoyo",
    "fuera_de_turno",
    "fecha_registro",
    "created_at",
]

# EIAG salio del catalogo de tipos de solicitante (quedo en ADM).
# Mismo criterio que el traspaso previo: 5 valores historicos -> los 4 validos.
EQUIVALENCIAS_SOLICITANTE = {"EIAG": "ADM"}

SQL = f"""
COPY (
    SELECT u."Email"                            AS tecnico_email,
           a."AreaSolicitante"                  AS area,
           coalesce(c."Email", '')              AS colaborador_email,
           a."MedioSolicitud"                   AS medio_solicitud,
           a."UsuarioSolicitante"               AS usuario_solicitante,
           a."Categoria"                        AS categoria,
           a."Descripcion"                      AS descripcion,
           a."Solucion"                         AS solucion,
           coalesce(a."Observaciones", '')      AS observaciones,
           coalesce(a."EnlaceApoyo", '')        AS enlace_apoyo,
           a."FueraDeTurno"                     AS fuera_de_turno,
           a."FechaRegistro"                    AS fecha_registro,
           a."CreatedAt"                        AS created_at
    FROM "Atenciones" a
    JOIN "Usuarios" u ON u."Id" = a."UsuarioId"
    LEFT JOIN "Usuarios" c ON c."Id" = a."ColaboradorId"
    WHERE a."FechaRegistro" >= DATE '{DESDE}'
    ORDER BY a."Id"
) TO STDOUT WITH (FORMAT csv, HEADER true, NULL '')
"""


def _norm(texto: str) -> str:
    """minusculas, sin tildes, espacios colapsados."""
    s = unicodedata.normalize("NFKD", texto)
    return " ".join(
        "".join(c for c in s if not unicodedata.combining(c)).lower().split()
    )


def _leer(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def leer_prod() -> list[dict[str, str]]:
    salida = subprocess.run(
        [
            "docker",
            "exec",
            CONTENEDOR,
            "psql",
            "-U",
            "soporte",
            "-d",
            "soporte",
            "-c",
            SQL,
        ],
        capture_output=True,
        check=True,
    )
    texto = salida.stdout.decode("utf-8")
    return list(csv.DictReader(texto.splitlines()))


def construir_resolutor() -> dict[str, str]:
    """texto de prod -> codigo de area. Canonicos pasan directo; origenes por mapeo."""
    catalogo = {f["nombre"].strip(): f["codigo_area"].strip() for f in _leer(CATALOGO)}
    resolutor = dict(catalogo)
    for fila in _leer(MAPEO):
        resolutor[fila["area_actual"].strip()] = fila["codigo_destino"].strip()
    return resolutor


def transformar(
    filas: list[dict[str, str]], resolutor: dict[str, str]
) -> tuple[list[dict[str, str]], list[str]]:
    problemas: list[str] = []
    normalizado: list[dict[str, str]] = []
    norm_resolutor = {_norm(k): v for k, v in resolutor.items()}

    for fila in filas:
        area_prod = fila["area"].strip()
        codigo = resolutor.get(area_prod) or norm_resolutor.get(_norm(area_prod))
        if codigo is None:
            problemas.append(f"area sin resolver: {area_prod!r}")
            codigo = area_prod

        solicitante = fila["usuario_solicitante"].strip()
        solicitante = EQUIVALENCIAS_SOLICITANTE.get(solicitante, solicitante)
        if solicitante not in SOLICITANTES_VALIDOS:
            problemas.append(f"solicitante invalido: {solicitante!r}")

        medio = fila["medio_solicitud"].strip()
        if medio not in MEDIOS_VALIDOS:
            problemas.append(f"medio invalido: {medio!r}")

        categoria = fila["categoria"].strip()
        if categoria not in CATEGORIAS_VALIDAS:
            problemas.append(f"categoria invalida: {categoria!r}")

        normalizado.append(
            {
                "tecnico_email": fila["tecnico_email"].strip(),
                "area_codigo": codigo,
                "colaborador_email": fila["colaborador_email"].strip(),
                "medio_solicitud": medio,
                "usuario_solicitante": solicitante,
                "categoria": categoria,
                "descripcion": fila["descripcion"],
                "solucion": fila["solucion"],
                "observaciones": fila["observaciones"],
                "enlace_apoyo": fila["enlace_apoyo"],
                "fuera_de_turno": "true"
                if fila["fuera_de_turno"].strip() == "t"
                else "false",
                "fecha_registro": fila["fecha_registro"].strip(),
                "created_at": fila["created_at"].strip(),
            }
        )
    return normalizado, problemas


def main() -> int:
    print(f"leyendo prod ({CONTENEDOR}) desde {DESDE}...")
    crudas = leer_prod()
    print(f"  filas en prod: {len(crudas)}")

    resolutor = construir_resolutor()
    filas, problemas = transformar(crudas, resolutor)

    with open(SALIDA, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)

    areas = {f["area_codigo"] for f in filas}
    print(f"escrito: {SALIDA.name}")
    print(f"  filas             : {len(filas)}")
    print(f"  areas canonicas   : {len(areas)}")
    print(f"  con colaborador   : {sum(1 for f in filas if f['colaborador_email'])}")
    print(
        f"  fuera de turno    : {sum(1 for f in filas if f['fuera_de_turno'] == 'true')}"
    )
    print(f"  tecnicos          : {len({f['tecnico_email'] for f in filas})}")
    print(
        f"  rango             : {filas[0]['fecha_registro']} -> {filas[-1]['fecha_registro']}"
    )

    if problemas:
        print(f"\nPROBLEMAS ({len(problemas)}):")
        for p in problemas[:20]:
            print("  -", p)
        return 1
    print("\nsin problemas de catalogo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
