"""Unit tests for review slicing and verdict merging. No DB, no I/O."""

import pytest

from app.services.review_slices import (
    DEFAULT_BUDGET_LINES,
    merge_verdicts,
    slice_candidate,
)

BUDGET = 400


def _doc_items(count: int = 61) -> list[tuple[str, int]]:
    """61 doc paths with realistic sizes: 5..60 lines, deterministic."""
    return [
        (f"docs/specs/seccion-{i:02d}.md", 5 + (i * 7) % 56) for i in range(count)
    ]


def test_slices_respect_budget_and_cover_all_paths_in_order():
    assert DEFAULT_BUDGET_LINES == 400
    items = _doc_items()
    slices = slice_candidate(items, budget_lines=BUDGET)

    assert len(slices) > 1
    for chunk in slices:
        assert chunk["total_lines"] <= BUDGET
        assert chunk["over_budget"] is False

    packed = [path for chunk in slices for path in chunk["paths"]]
    assert packed == [path for path, _ in items]
    assert len(packed) == 61
    assert len(set(packed)) == 61


def test_single_path_over_budget_gets_its_own_flagged_slice():
    slices = slice_candidate([("docs/gigante.md", 900)], budget_lines=BUDGET)
    assert len(slices) == 1
    assert slices[0]["paths"] == ["docs/gigante.md"]
    assert slices[0]["total_lines"] == 900
    assert slices[0]["over_budget"] is True


def test_empty_candidate_yields_no_slices_and_ok_verdict():
    assert slice_candidate([], budget_lines=BUDGET) == []
    assert merge_verdicts([]) == "ok"


def test_merge_verdicts_worst_wins():
    assert merge_verdicts(["ok", "observacion", "ok"]) == "observacion"
    assert merge_verdicts(["ok", "bloqueador", "observacion"]) == "bloqueador"
    assert merge_verdicts(["observacion", "observacion"]) == "observacion"


def test_merge_verdicts_unknown_value_fails_closed():
    with pytest.raises(ValueError):
        merge_verdicts(["ok", "aprobado"])