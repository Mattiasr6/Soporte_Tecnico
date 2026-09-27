import bcrypt

from scripts.seed import ATENCIONES_CSV, PADRES, USUARIOS, _leer_csv, hash_password


def test_seed_constants_mirror_ef():
    assert len(USUARIOS) == 10
    assert len(PADRES) == 3
    assert [p[1] for p in PADRES] == ["administrativos", "academicos", "extras"]
    assert [p[2] for p in PADRES] == ["Administrativos", "Académicos", "Extras"]
    assert USUARIOS[-1][3] == "Auxiliar"


def test_el_csv_se_puede_deduplicar_por_created_at():
    """El cargador incremental empareja por created_at: si dos filas lo compartieran,
    una se perderia en silencio."""
    creados = [f["created_at"].strip() for f in _leer_csv(ATENCIONES_CSV)]
    assert creados, "el CSV de atenciones no puede estar vacio"
    assert len(creados) == len(set(creados))


def test_hash_is_bcrypt_compatible():
    hashed = hash_password("Soporte2026*")
    assert hashed.startswith("$2b$")
    assert bcrypt.checkpw(b"Soporte2026*", hashed.encode())
