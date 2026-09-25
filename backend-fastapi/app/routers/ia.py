"""GET/POST /api/ia/* — Wilmercito. ASESOR, nunca AUTORIDAD: solo lectura."""

import os
import re

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.errors import forbidden
from app.core.security import CurrentUser, is_privileged
from app.db.session import DbSession
from app.models.feedback_ia import FeedbackIA
from app.services import ia_retrieval

router = APIRouter(prefix="/api/ia", tags=["ia"])

UMBRAL_SIN_EVIDENCIA = 0.5
RECHAZO_EXACTO = "Solo puedo responder consultas sobre el sistema de soporte técnico."
SIN_DATO = "No tengo ese dato disponible."

# Capa 1/3: prefiltro jailbreak (el modelo 1.5B obedece la última instrucción;
# ver docs/integracion-llamacpp.md §6). Sin llamar al motor.
_JAILBREAK = re.compile(
    r"ignor\w*|olvida|reglas anteriores|a partir de ahora|act[úu]a como|"
    r"prompt del sistema|system prompt|DAN\b|jailbreak",
    re.IGNORECASE,
)

# Capa 3/3: si el modelo divaga fuera de tema, se normaliza al rechazo exacto.
_MARCAS_FUERA_DE_TEMA = (
    "deport", "noticia", "política", "politica", "chiste", "abeja",
    "lo siento, pero", "como modelo", "receta", "clima",
)

_SALUDO = re.compile(r"^(hola|buenas|buenos d[ií]as|buenas tardes|hey|qué tal)[.!?]*$", re.IGNORECASE)
SALUDO_RESPUESTA = (
    "¡Hola! Soy Wilmercito, el asistente del Sistema de Soporte Técnico. "
    "Pregúntame sobre atenciones, categorías, áreas, técnicos o reportes."
)
_IDENTIDAD = re.compile(
    r"qui[eé]n eres|qu[eé] eres|c[óo]mo te llamas|tu nombre|pres[ée]ntate",
    re.IGNORECASE,
)
IDENTIDAD_RESPUESTA = (
    "Soy Wilmercito, el asistente virtual del Sistema de Soporte Técnico. "
    "Te ayudo con atenciones, categorías, medios de solicitud, áreas, "
    "técnicos, turnos, estados y reportes. ¿En qué te ayudo?"
)
# Preguntas de uso ("cómo creo..."): el embedding de frases largas y educadas
# deriva lejos; atajo determinista al doc curado correspondiente.
_CREAR_ATENCION = re.compile(
    r"c[óo]mo (creo|crear|registro|registrar|genero|hago|subo|agrego)"
    r"|crear (una |un )?(nueva |nuevo )?(atenci[óo]n|ticket)"
    r"|nueva atenci[óo]n|nuevo ticket",
    re.IGNORECASE,
)
# "¿tú podrías hacerlo por mí?": respuesta honesta de capacidades, sin modelo.
_CAPACIDAD = re.compile(
    r"(p+[ou]edes|podr[íi]as|ser[íi]as capaz|te animas).{0,30}"
    r"(hacerlo|crearlo|cambiarlo|hacer|crear|por m[ií]|por tu cuenta)",
    re.IGNORECASE,
)
CAPACIDAD_RESPUESTA = (
    "Todavía no puedo hacer cambios por ti: solo leo y explico. "
    "Puedo buscar casos parecidos, decirte cómo crear una atención y responder "
    "sobre categorías, áreas, técnicos y reportes. Si me calificas con 👍/👎, "
    "aprendo para la próxima."
)
# Sin evidencia pero con candidato cercano: ofrecerlo marcado como sugerencia
# en vez de un "no" seco (límite 0.9, bien lejos del umbral 0.5).
UMBRAL_SUGERENCIA = 0.9


def fuente_label(fuente: str | None) -> str | None:
    """Etiqueta legible para técnicos (nunca IDs internos en el chat)."""
    if not fuente:
        return None
    if fuente.startswith("atencion_"):
        return f"Atención #{fuente[len('atencion_'):]}"
    if fuente.startswith("feedback_"):
        return "Conocimiento del equipo"
    if fuente.startswith("usuario_"):
        return "Personal del sistema"
    if fuente.startswith("area_"):
        return "Organización"
    if fuente == "estadisticas":
        return "Datos del sistema"
    if fuente.startswith("kb_"):
        return "Base de conocimiento"
    return fuente


_ESTADISTICAS = re.compile(
    r"cu[áa]ntas atenciones|n[úu]mero de atenciones|total de atenciones"
    r"|atenciones (este|del) mes|resumen del (mes|sistema)",
    re.IGNORECASE,
)


def _estadisticas(db: DbSession) -> dict[str, object]:
    from datetime import date

    from sqlalchemy import func, select

    from app.models.atencion import Atencion

    total = db.execute(select(func.count()).select_from(Atencion)).scalar() or 0
    mes = db.execute(
        select(func.count())
        .select_from(Atencion)
        .where(Atencion.fecha_registro >= date.today().replace(day=1))
    ).scalar() or 0
    top = db.execute(
        select(Atencion.categoria, func.count().label("n"))
        .group_by(Atencion.categoria)
        .order_by(func.count().desc())
        .limit(3)
    ).all()
    detalle = ", ".join(f"{c}: {n}" for c, n in top)
    return {
        "respuesta": (
            f"Hay {total} atenciones registradas, {mes} este mes. "
            f"Por categoría: {detalle}."
        ),
        "fuente": "estadisticas",
        "fuente_label": fuente_label("estadisticas"),
        "rechazado": False,
    }

WILMERCITO_SYSTEM = """Eres Wilmercito, el asistente virtual del Sistema de Soporte Técnico.
Solo respondes sobre: atenciones, categorías, medios de solicitud, áreas/grupos/jerarquía,
técnicos/jefes/turnos, estados y dashboard/reportes.
Fuera de tema responde exactamente: "Solo puedo responder consultas sobre el sistema de soporte técnico."
No inventes: sin dato responde exactamente: "No tengo ese dato disponible."
Usa solo el Contexto entregado. Breve, claro, siempre en español."""


class BuscarIn(BaseModel):
    texto: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


@router.post("/buscar")
def buscar(body: BuscarIn, db: DbSession, user: CurrentUser):
    resultados = ia_retrieval.buscar(body.texto, body.top_k)
    if resultados and float(resultados[0]["distancia"]) > UMBRAL_SIN_EVIDENCIA:
        return {"resultados": [], "sin_evidencia": True}
    return {"resultados": resultados, "sin_evidencia": False}


@router.post("/reindexar")
def reindexar(db: DbSession, user: CurrentUser):
    return ia_retrieval.indexar(db)


@router.get("/estado")
def estado(db: DbSession, user: CurrentUser):
    try:
        _, col = ia_retrieval._lazy()
        return {"indexadas": col.count(), "modelo": "ok"}
    except Exception as e:  # dependencias IA aún no instaladas
        return {"indexadas": 0, "modelo": f"no-disponible: {e.__class__.__name__}"}


class PreguntarIn(BaseModel):
    pregunta: str = Field(min_length=3, max_length=500)


def _llama_chat(system: str, user: str) -> str:
    base = os.environ.get("LLAMA_URL", "http://100.78.144.4:8081").rstrip("/")
    key = os.environ.get("LLAMA_API_KEY", "")
    r = httpx.post(
        f"{base}/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=float(os.environ.get("LLAMA_TIMEOUT", "120")),
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


@router.post("/preguntar")
def preguntar(body: PreguntarIn, db: DbSession, user: CurrentUser):
    if _JAILBREAK.search(body.pregunta):
        return {"respuesta": RECHAZO_EXACTO, "fuente": None, "rechazado": True}
    if _SALUDO.search(body.pregunta.strip()):
        return {"respuesta": SALUDO_RESPUESTA, "fuente": "kb_saludo", "fuente_label": fuente_label("kb_saludo"), "rechazado": False}
    if _IDENTIDAD.search(body.pregunta):
        return {"respuesta": IDENTIDAD_RESPUESTA, "fuente": "kb_identidad", "fuente_label": fuente_label("kb_identidad"), "rechazado": False}
    if _CREAR_ATENCION.search(body.pregunta):
        doc = ia_retrieval.por_id("kb_nueva")
        if doc:
            return {"respuesta": doc["solucion"], "fuente": "kb_nueva", "fuente_label": fuente_label("kb_nueva"), "rechazado": False}
    if _CAPACIDAD.search(body.pregunta):
        return {"respuesta": CAPACIDAD_RESPUESTA, "fuente": None, "rechazado": False}
    if _ESTADISTICAS.search(body.pregunta):
        return _estadisticas(db)
    resultados = ia_retrieval.buscar(body.pregunta, 3)
    if not resultados or float(resultados[0]["distancia"]) > UMBRAL_SIN_EVIDENCIA:
        top = resultados[0] if resultados else None
        if top and float(top["distancia"]) <= UMBRAL_SUGERENCIA:
            return {
                "respuesta": (
                    "No encontré un caso igual, pero quizás te sirva este parecido "
                    f"(distancia {float(top['distancia']):.2f}, no verificado): "
                    f"{top['descripcion']} — Solución: {top['solucion']}"
                ),
                "fuente": top["id"],
                "fuente_label": fuente_label(top["id"]),
                "rechazado": False,
                "sugerencia": True,
            }
        return {"respuesta": SIN_DATO, "fuente": None, "rechazado": False}
    top = resultados[0]
    contexto = f"Context: [{top['id']}] {top['solucion']}"
    try:
        respuesta = _llama_chat(
            WILMERCITO_SYSTEM, f"{contexto}\n\nQuestion: {body.pregunta}\nAnswer:"
        )
    except (httpx.ConnectError, httpx.TimeoutException):
        return JSONResponse(status_code=503, content={"detail": "motor-ia-no-disponible"})
    if any(m in respuesta.lower() for m in _MARCAS_FUERA_DE_TEMA):
        return {"respuesta": RECHAZO_EXACTO, "fuente": None, "rechazado": True}
    return {"respuesta": respuesta, "fuente": top["id"], "fuente_label": fuente_label(top["id"]), "rechazado": False}


class CalificarIn(BaseModel):
    pregunta: str = Field(min_length=3, max_length=500)
    respuesta: str = Field(min_length=1, max_length=2000)
    fuente: str | None = Field(default=None, max_length=100)
    puntaje: int = Field(ge=1, le=4)


@router.post("/calificar")
def calificar(body: CalificarIn, db: DbSession, user: CurrentUser):
    from datetime import datetime, timezone

    db.add(
        FeedbackIA(
            usuario_id=user.id,
            pregunta=body.pregunta[:500],
            respuesta=body.respuesta[:2000],
            fuente=body.fuente,
            puntaje=body.puntaje,
            promovido=False,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return {"ok": True}


def _exigir_jefe_ia(user: CurrentUser) -> None:
    if not is_privileged(user):
        raise forbidden("Solo un jefe puede curar el conocimiento")


@router.get("/feedback")
def feedback_pendiente(db: DbSession, user: CurrentUser):
    from sqlalchemy import select

    _exigir_jefe_ia(user)
    filas = (
        db.execute(
            select(FeedbackIA)
            .where(FeedbackIA.puntaje >= 3, FeedbackIA.promovido.is_(False))
            .order_by(FeedbackIA.id.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": f.id,
            "pregunta": f.pregunta,
            "respuesta": f.respuesta,
            "fuente": f.fuente,
            "puntaje": f.puntaje,
        }
        for f in filas
    ]


@router.post("/feedback/{fid}/promover")
def feedback_promover(fid: int, db: DbSession, user: CurrentUser):
    _exigir_jefe_ia(user)
    fb = db.get(FeedbackIA, fid)
    if fb is None:
        return JSONResponse(status_code=404, content={"detail": "no-existe"})
    ia_retrieval.promover(feedback_id=fb.id, pregunta=fb.pregunta, respuesta=fb.respuesta)
    fb.promovido = True
    db.commit()
    return {"ok": True, "fuente": f"feedback_{fb.id}"}
