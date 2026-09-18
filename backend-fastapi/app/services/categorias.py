CATEGORIAS_VALIDAS = frozenset(
    {
        "Audio/Video",
        "Cuentas/Accesos",
        "Hardware",
        "Impresión",
        "Otros",
        "Redes/Conectividad",
        "Sistemas académicos",
        "Software",
    }
)

_NORMALIZAR = {
    "impresion": "Impresión",
    "cuentas": "Cuentas/Accesos",
    "sistemas academicos": "Sistemas académicos",
    "otros": "Otros",
}


def normalizar_categoria(cat: str) -> str:
    return _NORMALIZAR.get(cat.strip().lower(), cat)
