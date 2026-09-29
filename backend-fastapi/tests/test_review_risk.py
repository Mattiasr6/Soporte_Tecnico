"""Unit tests for the local review risk classifier. No DB, no I/O."""

from app.services.review_risk import classify_candidate, classify_path

DOC_BUNDLE = [f"docs/specs/seccion-{i:02d}.md" for i in range(31)] + [
    f"docs/anexos/anexo-{i:02d}.pdf" for i in range(30)
]


def test_doc_bundle_is_pasivo():
    assert len(DOC_BUNDLE) == 61
    result = classify_candidate(DOC_BUNDLE)
    assert result["tier"] == "pasivo"
    assert len(result["por_path"]) == 61
    assert result["motivo"] == "all paths passive docs"


def test_pdf_path_is_opaco_and_name_does_not_raise_risk():
    path = "docs/pdf/docs/spec-s5-auth.pdf"
    assert classify_path(path) == "opaco"
    assert classify_candidate([path])["tier"] == "opaco"


def test_python_among_docs_is_activo():
    result = classify_candidate([*DOC_BUNDLE, "app/services/review_risk.py"])
    assert result["tier"] == "activo"
    assert result["motivo"] == "1 active paths (max tier)"


def test_env_path_is_critico():
    assert classify_path(".env") == "critico"
    result = classify_candidate([*DOC_BUNDLE, ".env"])
    assert result["tier"] == "critico"
    assert result["motivo"] == "critical path: .env"


def test_unknown_extension_fails_closed():
    assert classify_path("data/blob.xyz") == "activo"
    assert classify_candidate(["data/blob.xyz"])["tier"] == "activo"


def test_empty_candidate_is_pasivo():
    result = classify_candidate([])
    assert result["tier"] == "pasivo"
    assert result["por_path"] == []
    assert "empty" in result["motivo"].lower()
