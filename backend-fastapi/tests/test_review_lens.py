"""Unit tests for the local review lens. No GPU, no network (fake caller)."""

import pytest

from app.services.review_lens import (
    build_lens_prompt,
    corroborate,
    parse_verdict,
    run_review,
)

DIFF = "--- a/x.py\n+++ b/x.py\n@@\n+password = '123'\n"


def test_unknown_lens_raises():
    with pytest.raises(ValueError):
        build_lens_prompt("perfume", DIFF)


def test_parse_verdict_ok():
    assert parse_verdict("VEREDICTO: ok\nnada que ver") == "ok"


def test_parse_unparseable_is_observacion_not_ok():
    assert parse_verdict("todo mal, sin formato") == "observacion"
    assert parse_verdict("") == "observacion"


def test_single_blocker_downgraded():
    votes = {"riesgo": "bloqueador", "resiliencia": "ok",
             "legibilidad": "ok", "confiabilidad": "ok"}
    assert corroborate(votes) == "observacion"


def test_two_blockers_block():
    votes = {"riesgo": "bloqueador", "resiliencia": "bloqueador",
             "legibilidad": "ok", "confiabilidad": "ok"}
    assert corroborate(votes) == "bloqueador"


def test_all_ok_is_ok():
    assert corroborate({v: "ok" for v in
                         ("riesgo", "resiliencia", "legibilidad", "confiabilidad")}) == "ok"


def test_run_review_with_fake_caller():
    def fake(system, user):
        return "VEREDICTO: ok\nlimpio" if "legibilidad" in system else "VEREDICTO: observacion\nmirar"
    out = run_review(DIFF, caller=fake)
    assert set(out["votes"]) == {"riesgo", "resiliencia", "legibilidad", "confiabilidad"}
    assert out["verdict"] == "observacion"
