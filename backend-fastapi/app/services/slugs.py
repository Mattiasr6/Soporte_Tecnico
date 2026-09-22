"""Codigo estable (slug) para los nodos del catalogo de jerarquia.

El codigo es la identidad del nodo y NO cambia cuando se renombra. Eso es lo que
permite que los CSV de bootstrap y la historia de atenciones sigan siendo validos
aunque un area cambie de nombre cada gestion.
"""

import unicodedata


def slugify(texto: str, maximo: int = 60) -> str:
    """'Académicos Modular' -> 'academicos-modular'."""
    s = unicodedata.normalize("NFKD", texto)
    s = "".join(c for c in s if not unicodedata.combining(c))
    limpio = "".join(c if c.isalnum() else "-" for c in s.lower())
    return "-".join(p for p in limpio.split("-") if p)[:maximo]


def codigo_unico(base: str, usados: set[str]) -> str:
    """Evita colisiones al crear: sistemas, sistemas-2, sistemas-3..."""
    if base not in usados:
        return base
    n = 2
    while f"{base}-{n}" in usados:
        n += 1
    return f"{base}-{n}"
