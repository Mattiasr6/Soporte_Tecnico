"""Retrieval semántico para Wilmercito (Fase 1: búsqueda, alucinación = 0).

Solo lectura: indexa Descripcion -> vector y devuelve tickets reales con su
Solución. Sin texto generado: lo que se muestra existe en la base.
"""

import os
from typing import Any

# ponytail: estos imports son pesados; se cargan lazy en _lazy() para no
# penalizar el arranque de la API cuando /ia/* no se usa.
_chroma = None
_model = None


def _lazy():
    global _chroma, _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(
            os.environ.get("EMB_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        )
    if _chroma is None:
        import chromadb

        client = chromadb.PersistentClient(
            path=os.environ.get("CHROMA_DIR", "./chroma_db")
        )
        _chroma = client.get_or_create_collection("atenciones")
    return _model, _chroma


def embed(texto: str) -> list[float]:
    model, _ = _lazy()
    # .tolist() obligatorio: Chroma exige list, no numpy array
    # (bug «RAG mudo» del proyecto donante).
    # normalize_embeddings: con vectores unitarios, la distancia L2 de Chroma
    # equivale a distancia coseno (0..2) y el umbral es estable.
    return model.encode([texto.lower()], normalize_embeddings=True)[0].tolist()


_KB_ESTATICA: list[tuple[str, str, str]] = [
    (
        "kb_categorias",
        "cuales son las categorias de atencion",
        "Las 8 categorías válidas son: Audio/Video, Cuentas/Accesos, Hardware, "
        "Impresión, Otros, Redes/Conectividad, Sistemas académicos y Software.",
    ),
    (
        "kb_medios",
        "cuales son los medios de solicitud",
        "Los medios de solicitud son: Interno, Presencial, WhatsApp y E-ticket.",
    ),
    (
        "kb_tipos",
        "cuales son los tipos de solicitante",
        "Los tipos de solicitante son: ADM, BEC, DOC, EST y EIAG.",
    ),
]


def indexar(db) -> dict[str, Any]:
    """Indexa todas las Atenciones. Idempotente: re-ejecutar omite existentes."""
    from sqlalchemy import select

    from app.models.atencion import Atencion

    model, col = _lazy()
    existentes = set(col.get(ids=None, include=[])["ids"])
    nuevas = 0
    for a in db.execute(select(Atencion)).scalars().all():
        pid = f"atencion_{a.id}"
        if pid in existentes:
            continue
        col.add(
            ids=[pid],
            documents=[a.solucion or ""],
            metadatas=[
                {
                    "source": pid,
                    "question": a.descripcion or "",
                    "categoria": a.categoria or "",
                    "area": a.area_solicitante or "",
                }
            ],
            embeddings=[model.encode([(a.descripcion or "").lower()], normalize_embeddings=True)[0].tolist()],
        )
        nuevas += 1
    for pid, pregunta, documento in _KB_ESTATICA:
        if pid in existentes:
            continue
        col.add(
            ids=[pid],
            documents=[documento],
            metadatas=[
                {
                    "source": pid,
                    "question": pregunta,
                    "categoria": "",
                    "area": "",
                }
            ],
            embeddings=[model.encode([pregunta.lower()], normalize_embeddings=True)[0].tolist()],
        )
        nuevas += 1
    return {"nuevas": nuevas, "total": len(existentes) + nuevas}


def buscar(texto: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Top-k tickets parecidos. Umbral: distancia > 0.35 = sin evidencia."""
    _, col = _lazy()
    res = col.query(query_embeddings=[embed(texto)], n_results=top_k)
    out = []
    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i]
        out.append(
            {
                "id": meta["source"],
                "descripcion": meta["question"],
                "solucion": res["documents"][0][i],
                "categoria": meta["categoria"],
                "area": meta["area"],
                "distancia": res["distances"][0][i],
            }
        )
    return out
