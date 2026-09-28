"""Learn from review false positives (Phase 4: the review reviews itself).

A disagreement is logged when the provider tier, the local tier
(review_risk) and the human verdict differ for one candidate. Repeated
false positives sharing the same signal produce a tuning suggestion
(e.g. an allowlist entry), so the classifier improves instead of
repeating the same mistake.
"""

from typing import TypedDict

from app.services.review_risk import TIER_RANK


class Disagreement(TypedDict):
    provider: str
    local: str
    human: str
    signal: str
    false_positive: bool


def record_disagreement(
    provider_tier: str, local_tier: str, human_tier: str, signal: str
) -> Disagreement:
    """Log one verdict triple. A provider false positive is a provider tier
    strictly above the human verdict (fail-closed direction preserved: a
    provider tier *below* human is never a false positive)."""
    for tier in (provider_tier, local_tier, human_tier):
        if tier not in TIER_RANK:
            raise ValueError(f"unknown tier: {tier!r}")
    return {
        "provider": provider_tier,
        "local": local_tier,
        "human": human_tier,
        "signal": signal,
        "false_positive": TIER_RANK[provider_tier] > TIER_RANK[human_tier],
    }


def suggest_tuning(
    log: list[Disagreement], min_repeat: int = 2
) -> list[str]:
    """Suggest allowlist rules from repeated false positives sharing a signal.

    Returns human-readable suggestions like:
    'allowlist "auth in filename": cap provider tier at "opaco"'
    Only signals seen at least min_repeat times are suggested; a single
    disagreement is data, not a rule.
    """
    by_signal: dict[str, list[Disagreement]] = {}
    for entry in log:
        if entry["false_positive"]:
            by_signal.setdefault(entry["signal"], []).append(entry)

    suggestions: list[str] = []
    for signal, entries in sorted(by_signal.items()):
        if len(entries) >= min_repeat:
            cap = min(entries, key=lambda e: TIER_RANK[e["human"]])["human"]
            suggestions.append(
                f'allowlist "{signal}": cap provider tier at "{cap}" '
                f"({len(entries)} false positives)"
            )
    return suggestions
