import bcrypt

from scripts.seed import PADRES, USUARIOS, hash_password


def test_seed_constants_mirror_ef():
    assert len(USUARIOS) == 10
    assert len(PADRES) == 3
    assert [p[1] for p in PADRES] == ["Administrativos", "Académicos", "Extras"]
    assert USUARIOS[-1][3] == "Auxiliar"


def test_hash_is_bcrypt_compatible():
    hashed = hash_password("Soporte2026*")
    assert hashed.startswith("$2b$")
    assert bcrypt.checkpw(b"Soporte2026*", hashed.encode())
