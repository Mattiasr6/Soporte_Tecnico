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
        "kb_identidad",
        "hola quien eres wilmercito que eres tu",
        "Soy Wilmercito, el asistente virtual del Sistema de Soporte Técnico. "
        "Te ayudo con atenciones, categorías, medios de solicitud, áreas, "
        "técnicos, turnos, estados y reportes. ¿En qué te ayudo?",
    ),
    (
        "kb_saludo",
        "hola buenas dias tardes como estas",
        "¡Hola! Soy Wilmercito, el asistente del Sistema de Soporte Técnico. "
        "Pregúntame sobre atenciones, categorías, áreas, técnicos o reportes.",
    ),
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
    (
        "kb_nueva",
        "como creo una nueva atencion como registrar atencion crear ticket "
        "podrias decirme como puedo crear una nueva atencion donde registro tickets",
        "Para crear una atención: entra a Atenciones, Nueva atención. 1) Elige el "
        "área en el selector de jerarquía. 2) Medio de solicitud, tipo de solicitante "
        "y una de las 8 categorías. 3) Describe el problema y su solución "
        "(observaciones y enlace de apoyo son opcionales). 4) Pulsa Agregar a la "
        "lista (puedes cargar varias) y luego confirma para guardarlas. "
        "Aparecerán en la lista de Atenciones.",
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
        # La KB curada se re-escribe siempre: así se puede corregir sin versionar ids.
        if pid in existentes:
            col.delete(ids=[pid])
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
    return {"nuevas": nuevas, "total": col.count()}


def por_id(pid: str) -> dict[str, Any] | None:
    """Devuelve un documento curado por id (para atajos deterministas)."""
    _, col = _lazy()
    res = col.get(ids=[pid])
    if not res["ids"]:
        return None
    return {
        "id": pid,
        "descripcion": res["metadatas"][0]["question"],
        "solucion": res["documents"][0],
        "categoria": res["metadatas"][0]["categoria"],
        "area": res["metadatas"][0]["area"],
        "distancia": 0.0,
    }


def promover(feedback_id: int, pregunta: str, respuesta: str) -> str:
    """Indexa un feedback aprobado por un jefe. Id es estable: re-promover pisa."""
    model, col = _lazy()
    pid = f"feedback_{feedback_id}"
    if col.get(ids=[pid])["ids"]:
        col.delete(ids=[pid])
    col.add(
        ids=[pid],
        documents=[respuesta],
        metadatas=[
            {"source": pid, "question": pregunta, "categoria": "", "area": ""}
        ],
        embeddings=[model.encode([pregunta.lower()], normalize_embeddings=True)[0].tolist()],
    )
    return pid


def buscar(texto: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Top-k tickets parecidos. El umbral vive en el router."""
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
