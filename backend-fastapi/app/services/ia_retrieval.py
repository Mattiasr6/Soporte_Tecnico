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
        "cuales son las categorias de atencion | categorías | lista de categorías",
        "Las 8 categorías válidas son: Audio/Video, Cuentas/Accesos, Hardware, "
        "Impresión, Otros, Redes/Conectividad, Sistemas académicos y Software.",
    ),
    (
        "kb_medios",
        "cuales son los medios de solicitud | medios | canales de solicitud",
        "Los medios de solicitud son: Interno, Presencial, WhatsApp y E-ticket.",
    ),
    (
        "kb_tipos",
        "cuales son los tipos de solicitante | tipos de solicitante | solicitantes",
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
    """Indexa Atenciones + Usuarios + Áreas. Idempotente en tickets y KB."""
    from sqlalchemy import select

    from app.models.area import Area
    from app.models.atencion import Atencion
    from app.models.grupo import Grupo
    from app.models.usuario import Usuario

    model, col = _lazy()
    existentes = set(col.get(ids=None, include=[])["ids"])
    nuevas = 0
    _nombres = {
        u.id: u.display_name
        for u in db.execute(select(Usuario)).scalars().all()
    }
    def _agregar(pid, pregunta, documento, categoria="", area="", titulo=""):
        if pid in existentes:
            return
        col.add(
            ids=[pid],
            documents=[documento],
            metadatas=[
                {
                    "source": pid,
                    "question": pregunta,
                    "titulo": titulo or pregunta,
                    "categoria": categoria,
                    "area": area,
                }
            ],
            embeddings=[model.encode([pregunta.lower()], normalize_embeddings=True)[0].tolist()],
        )

    for a in db.execute(select(Atencion)).scalars().all():
        ficha = (
            f"{a.descripcion or ''}\nSolución: {a.solucion or ''}"
            f"\nCategoría: {a.categoria or ''} · Área: {a.area_solicitante or ''}"
            f" · Medio: {a.medio_solicitud or ''}"
            f"\nRegistrada por: {_nombres.get(a.usuario_id, '—')}"
        )
        if a.observaciones:
            ficha += f"\nObservaciones: {a.observaciones}"
        _agregar(
            f"atencion_{a.id}",
            f"{a.descripcion or ''} {a.categoria or ''} {a.area_solicitante or ''}",
            ficha,
            a.categoria or "",
            a.area_solicitante or "",
            a.descripcion or "",
        )
        nuevas += 1
    for u in db.execute(select(Usuario).where(Usuario.activo.is_(True))).scalars().all():
        pid = f"usuario_{u.id}"
        if pid in existentes:
            continue
        _agregar(
            pid,
            f"{u.display_name} {u.especialidad or ''} {u.role}",
            f"{u.display_name} es {u.role}"
            + (f" ({u.especialidad})" if u.especialidad else "")
            + ".",
            "",
            "",
            u.display_name,
        )
        nuevas += 1
    grupos = {g.id: g.nombre for g in db.execute(select(Grupo)).scalars().all()}
    for ar in db.execute(select(Area).where(Area.activo.is_(True))).scalars().all():
        pid = f"area_{ar.id}"
        if pid in existentes:
            continue
        grupo = grupos.get(ar.grupo_id, "")
        _agregar(
            pid,
            f"área {ar.nombre} {grupo}",
            f"El área {ar.nombre} (código {ar.codigo or '—'})"
            + (f" pertenece al grupo {grupo}." if grupo else "."),
            "",
            "",
            ar.nombre,
        )
        nuevas += 1
    from app.models.feedback_ia import FeedbackIA

    for fb in db.execute(
        select(FeedbackIA).where(FeedbackIA.promovido.is_(True))
    ).scalars().all():
        pid = f"feedback_{fb.id}"
        if pid in existentes:
            continue
        _agregar(pid, fb.pregunta, fb.respuesta)
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
        "descripcion": res["metadatas"][0].get("titulo") or res["metadatas"][0]["question"],
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
    """Híbrido vectorial + BM25 con fusión RRF. El umbral vive en el router."""
    import re as _re

    texto = _re.sub(
        r"^(y|entonces|pero|adem[áa]s|ahora|oye)\s+", "", texto.strip(), flags=_re.IGNORECASE
    )
    _, col = _lazy()
    n_cand = max(top_k * 4, 12)
    res = col.query(query_embeddings=[embed(texto)], n_results=n_cand)
    ids: list[str] = res["ids"][0]
    docs: list[str] = res["documents"][0]
    metas: list[dict[str, Any]] = res["metadatas"][0]
    dists = dict(zip(ids, res["distances"][0], strict=False))
    orden = _fusion_rrf(ids, _bm25_top(texto, [m["question"] for m in metas], ids))
    orden = _rerank_idx(texto, docs, orden)
    out = []
    for i in orden[:top_k]:
        meta = metas[i]
        out.append(
            {
                "id": ids[i],
                "descripcion": meta.get("titulo") or meta["question"],
                "solucion": docs[i],
                "categoria": meta["categoria"],
                "area": meta["area"],
                "distancia": dists[ids[i]],
            }
        )
    return out


def _tokens(texto: str) -> list[str]:
    import re
    import unicodedata

    nfkd = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    return re.findall(r"[a-z0-9]+", nfkd)


_bm25 = None
_bm25_ids: list[str] = []


def _bm25_top(texto: str, preguntas: list[str], ids: list[str]) -> list[int]:
    """Índices de candidatos por BM25 (keywords exactas: IDs, códigos)."""
    global _bm25
    try:
        if _bm25 is None:
            from rank_bm25 import BM25Okapi

            _bm25 = BM25Okapi([_tokens(p) for p in preguntas])
        scores = _bm25.get_scores(_tokens(texto))
        return sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)
    except Exception:  # noqa: BLE001 - BM25 opcional: sin el, orden plano
        return list(range(len(ids)))


def _fusion_rrf(ids: list[str], orden_bm25: list[int], k: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: vector (orden dado) + BM25. Devuelve índices."""
    puntaje = {i: 1.0 / (k + r + 1) for r, i in enumerate(range(len(ids)))}
    for r, i in enumerate(orden_bm25):
        puntaje[i] = puntaje.get(i, 0.0) + 1.0 / (k + r + 1)
    return sorted(puntaje.keys(), key=lambda i: puntaje[i], reverse=True)


def _rerank_idx(texto: str, docs: list[str], orden: list[int]) -> list[int]:
    sub = [docs[i] for i in orden]
    nuevo = _rerank(texto, sub)
    return [orden[i] for i in nuevo]


_reranker = None


def _rerank(pregunta: str, docs: list[str]) -> list[int]:
    """Ordena candidatos por relevancia real. Apagado por defecto (RERANK=1).

    Medido 2026-09-25: mmarco-mMiniLMv2 reordena mal en este dominio
    (KB exacta 6ta de 12); el bi-encoder solo acierta. Se conserva el código
    para el informe y futuros modelos.
    """
    global _reranker
    if os.environ.get("RERANK", "0") != "1":
        return list(range(len(docs)))
    try:
        if _reranker is None:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(
                os.environ.get(
                    "RERANK_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
                )
            )
        scores = _reranker.predict([(pregunta, d) for d in docs])
        return sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    except Exception:  # noqa: BLE001 - reranker opcional: sin el, orden plano
        return list(range(len(docs)))


def similares_a_ticket(pid: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Casos parecidos a un ticket dado (por su propio vector, sin texto)."""
    _model, col = _lazy()
    base = col.get(ids=[pid], include=["embeddings", "metadatas", "documents"])
    if not base["ids"]:
        return []
    res = col.query(query_embeddings=base["embeddings"], n_results=top_k + 1)
    out = []
    for i in range(len(res["ids"][0])):
        if res["ids"][0][i] == pid:
            continue
        meta = res["metadatas"][0][i]
        out.append(
            {
                "id": res["ids"][0][i],
                "descripcion": meta.get("titulo") or meta["question"],
                "solucion": res["documents"][0][i],
                "categoria": meta["categoria"],
                "area": meta["area"],
                "distancia": res["distances"][0][i],
            }
        )
        if len(out) >= top_k:
            break
    return out


INTENCIONES: dict[str, list[str]] = {
    "saludo": ["hola", "buenas", "buenos días", "buenas tardes", "hey"],
    "identidad": [
        "quién eres",
        "cómo te llamas",
        "preséntate",
        "qué eres",
        "tu nombre",
    ],
    "crear": [
        "cómo creo una atención",
        "cómo registro un ticket",
        "dónde creo tickets",
        "quiero cargar una atención nueva",
    ],
    "capacidad": [
        "puedes hacerlo por mí",
        "serías capaz de ayudarme",
        "puedes crearla tú",
        "hazlo por tu cuenta",
    ],
    "estadisticas": [
        "cuántas atenciones hay",
        "número de atenciones este mes",
        "resumen del sistema",
        "informe del mes",
    ],
}

_intent_vecs: dict[str, Any] | None = None


def clasificar(texto: str) -> tuple[str | None, float]:
    """Intent por similitud semántica (ejemplos, no palabras).

    Devuelve (intent, similitud). Umbral + margen anti-ambigüedad calibrados
    en docs/integracion-llamacpp.md §5e.
    """
    import numpy as np

    global _intent_vecs
    model, _ = _lazy()
    if _intent_vecs is None:
        _intent_vecs = {
            k: model.encode(v, normalize_embeddings=True) for k, v in INTENCIONES.items()
        }
    assert _intent_vecs is not None
    q = model.encode([texto.lower()], normalize_embeddings=True)[0]
    mejor, mejor_sim, segunda = None, -1.0, -1.0
    for intent, vecs in _intent_vecs.items():
        sim = float(np.max(vecs @ q))
        if sim > mejor_sim:
            segunda, mejor, mejor_sim = mejor_sim, intent, sim
        elif sim > segunda:
            segunda = sim
    if mejor_sim >= 0.55 and mejor_sim - segunda >= 0.08:
        return mejor, mejor_sim
    return None, mejor_sim
