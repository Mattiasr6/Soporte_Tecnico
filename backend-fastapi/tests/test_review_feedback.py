"""Unit tests for the review false-positive loop. No DB, no I/O."""

import pytest

from app.services.review_feedback import record_disagreement, suggest_tuning


def test_provider_high_vs_human_pasivo_is_false_positive():
    d = record_disagreement("activo", "pasivo", "pasivo", "auth in filename")
    assert d["false_positive"] is True


def test_provider_below_human_is_never_false_positive():
    d = record_disagreement("pasivo", "pasivo", "activo", "docs bundle")
    assert d["false_positive"] is False


def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        record_disagreement("alto", "pasivo", "pasivo", "x")


def test_repeated_signal_suggests_allowlist():
    log = [
        record_disagreement("activo", "opaco", "opaco", "auth in filename"),
        record_disagreement("activo", "opaco", "opaco", "auth in filename"),
    ]
    out = suggest_tuning(log)
    assert len(out) == 1
    assert 'allowlist "auth in filename"' in out[0]
    assert '"opaco"' in out[0]


def test_single_disagreement_suggests_nothing():
    log = [record_disagreement("activo", "opaco", "opaco", "auth in filename")]
    assert suggest_tuning(log) == []


def test_no_false_positives_suggests_nothing():
    log = [record_disagreement("pasivo", "pasivo", "pasivo", "docs")]
    assert suggest_tuning(log) == []
