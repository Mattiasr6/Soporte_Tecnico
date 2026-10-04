"""Local review lens over the project's own llama.cpp engine (Phase 3).

Four passes (riesgo, resiliencia, legibilidad, confiabilidad) vote
'bloqueador' / 'observacion' / 'ok' on a unified diff. Only findings
corroborated by 2+ lenses block; the rest go to the log as follow-ups.
Model I/O is isolated in _llama_chat (same shape as routers/ia.py) and
injectable via run_review(..., caller=...) so tests never touch the GPU.
"""

import os
from collections.abc import Callable
from typing import TypedDict

import httpx

LENSES = ("riesgo", "resiliencia", "legibilidad", "confiabilidad")

VERDICTS = ("bloqueador", "observacion", "ok")

_LENS_FOCUS = {
    "riesgo": "secretos expuestos, validacion de entradas en bordes de confianza, autorizacion y exfiltracion de datos",
    "resiliencia": "reintentos, degradacion elegante, manejo de errores, observabilidad y rollback",
    "legibilidad": "nombres, complejidad, intencion del codigo y mantenibilidad",
    "confiabilidad": "tests con valor, casos borde, determinismo y regresiones",
}

_SYSTEM_TMPL = (
    "Sos un revisor de codigo {lens} y tu unico foco es: {focus}. "
    "Recibis un diff unificado. Respondes con EXACTAMENTE una primera linea "
    "que sea uno de: VEREDICTO: bloqueador | VEREDICTO: observacion | VEREDICTO: ok. "
    "Despues, hasta 5 lineas con el hallazgo concreto (archivo:linea, problema, fix). "
    "Si no hay nada en tu foco, vota ok. No inventes problemas fuera de tu foco."
)


def build_lens_prompt(lens: str, diff_text: str) -> tuple[str, str]:
    """Return (system, user) messages for one lens over a diff."""
    if lens not in _LENS_FOCUS:
        raise ValueError(f"unknown lens: {lens!r}")
    system = _SYSTEM_TMPL.format(lens=lens, focus=_LENS_FOCUS[lens])
    user = f"Revisa este diff:\n\n{diff_text[:8000]}"
    return system, user


def parse_verdict(text: str) -> str:
    """Extract the vote from a lens reply. Unparseable replies become
    'observacion' (human eyes required) — never a silent ok, never noise."""
    first = (text or "").strip().splitlines()
    head = first[0].lower() if first else ""
    for verdict in VERDICTS:
        if f"veredicto: {verdict}" in head:
            return verdict
    return "observacion"


def corroborate(votes: dict[str, str]) -> str:
    """Worst-wins, but 'bloqueador' needs 2+ lenses (single-lens blockers
    are downgraded to 'observacion'). Empty votes -> 'ok'."""
    for verdict in votes.values():
        if verdict not in VERDICTS:
            raise ValueError(f"unknown verdict: {verdict!r}")
    counts = [v for v in votes.values()]
    if counts.count("bloqueador") >= 2:
        return "bloqueador"
    if "bloqueador" in counts or "observacion" in counts:
        return "observacion"
    return "ok"


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


class LensResult(TypedDict):
    lens: str
    verdict: str
    raw: str


class ReviewResult(TypedDict):
    votes: dict[str, str]
    verdict: str
    details: list[LensResult]


def run_review(
    diff_text: str, caller: Callable[[str, str], str] | None = None
) -> ReviewResult:
    """Run the 4 lenses over a diff. Returns {"votes": {...}, "verdict": ...}.
    Pass caller=fake in tests; default hits the local engine."""
    call = caller or _llama_chat
    results: list[LensResult] = []
    for lens in LENSES:
        system, user = build_lens_prompt(lens, diff_text)
        raw = call(system, user)
        results.append({"lens": lens, "verdict": parse_verdict(raw), "raw": raw})
    votes = {r["lens"]: r["verdict"] for r in results}
    return {"votes": votes, "verdict": corroborate(votes), "details": results}
