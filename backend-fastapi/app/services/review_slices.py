"""Slice a review candidate into fixed-budget chunks and merge verdicts.

A candidate with many paths can exceed the lens context budget. Slicing keeps
each review request under a line budget while preserving path order. A single
path larger than the budget still gets its own slice, flagged so the caller
can decide (review it alone, or skip it).

Pure functions, stdlib only, no I/O.
"""

from typing import TypedDict

DEFAULT_BUDGET_LINES = 400

# Ordered severity for verdict merging; worst wins.
VERDICT_RANK = {"ok": 0, "observacion": 1, "bloqueador": 2}


class ReviewSlice(TypedDict):
    paths: list[str]
    total_lines: int
    over_budget: bool


def slice_candidate(
    items: list[tuple[str, int]], budget_lines: int = DEFAULT_BUDGET_LINES
) -> list[ReviewSlice]:
    """Greedily pack (path, lines) pairs into slices under ``budget_lines``.

    Paths keep their input order and appear exactly once across slices. A
    single path larger than the budget gets its own slice with
    ``over_budget`` set to True.
    """
    slices: list[ReviewSlice] = []
    current_paths: list[str] = []
    current_lines = 0

    for path, lines in items:
        if current_paths and current_lines + lines > budget_lines:
            slices.append(
                {
                    "paths": current_paths,
                    "total_lines": current_lines,
                    "over_budget": False,
                }
            )
            current_paths = []
            current_lines = 0
        current_paths.append(path)
        current_lines += lines

    if current_paths:
        slices.append(
            {
                "paths": current_paths,
                "total_lines": current_lines,
                "over_budget": current_lines > budget_lines,
            }
        )
    return slices


def merge_verdicts(verdicts: list[str]) -> str:
    """Return the worst verdict: "ok" < "observacion" < "bloqueador".

    An empty list is "ok". Unknown values raise ValueError (fail closed:
    never silently downgrade an unrecognized verdict).
    """
    worst = "ok"
    for verdict in verdicts:
        if verdict not in VERDICT_RANK:
            raise ValueError(f"unknown verdict: {verdict!r}")
        if VERDICT_RANK[verdict] > VERDICT_RANK[worst]:
            worst = verdict
    return worst