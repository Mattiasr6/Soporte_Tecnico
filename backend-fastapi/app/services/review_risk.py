"""Risk classification for a local review candidate.

The candidate tier decides how much review machinery a set of changed paths
deserves. Rules are deterministic and based on the path itself; anything
unknown is treated as executable code (fail closed, full lenses).
"""

import os
import re
from typing import TypedDict

# Ordered severity for callers that need to compare tiers.
TIER_RANK = {"pasivo": 0, "opaco": 1, "activo": 2, "critico": 3}

CODE_EXTENSIONS = frozenset(
    {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".sql", ".html", ".vue"}
)
OPAQUE_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".mp4",
        ".zip",
        ".vmdk",
    }
)
DOC_EXTENSIONS = frozenset({".md", ".rst", ".txt"})

_PRIVATE_KEY = re.compile(r"private[._-]?key")


def classify_path(path: str) -> str:
    """Classify one path as 'pasivo', 'opaco', 'activo' or 'critico'."""
    base = os.path.basename(path).lower()
    lower = path.lower()

    if (
        base.startswith(".env")
        or "secret" in base
        or "credential" in base
        or _PRIVATE_KEY.search(base)
        or lower.endswith((".pem", ".key"))
    ):
        return "critico"

    ext = os.path.splitext(base)[1]
    parts = lower.replace("\\", "/").split("/")
    if (
        ext in CODE_EXTENSIONS
        or "alembic" in parts
        or "migrations" in parts
        or base.startswith("dockerfile")
        or base.startswith("docker-compose")
    ):
        return "activo"

    if ext in OPAQUE_EXTENSIONS:
        return "opaco"
    if ext in DOC_EXTENSIONS:
        return "pasivo"
    return "activo"  # fail closed: unknown content gets the full lenses


class PathTier(TypedDict):
    path: str
    tier: str


class CandidateRisk(TypedDict):
    tier: str
    por_path: list[PathTier]
    motivo: str


def classify_candidate(paths: list[str]) -> CandidateRisk:
    """Aggregate per-path tiers into the review tier of a whole candidate.

    Escalation is fail-closed: a critical path wins, then any active path.
    Below that, readable text docs set the pace (a docs bundle with attached
    PDFs/images is still passive); a bundle of only binaries is opaque.
    """
    if not paths:
        return {"tier": "pasivo", "por_path": [], "motivo": "empty candidate: no paths"}

    por_path: list[PathTier] = [
        {"path": p, "tier": classify_path(p)} for p in paths
    ]
    tiers = [item["tier"] for item in por_path]

    if "critico" in tiers:
        first = next(item["path"] for item in por_path if item["tier"] == "critico")
        return {"tier": "critico", "por_path": por_path, "motivo": f"critical path: {first}"}
    if "activo" in tiers:
        activos = tiers.count("activo")
        return {
            "tier": "activo",
            "por_path": por_path,
            "motivo": f"{activos} active paths (max tier)",
        }
    if "pasivo" in tiers:
        return {"tier": "pasivo", "por_path": por_path, "motivo": "all paths passive docs"}
    return {
        "tier": "opaco",
        "por_path": por_path,
        "motivo": f"{len(tiers)} opaque paths (no text docs)",
    }
