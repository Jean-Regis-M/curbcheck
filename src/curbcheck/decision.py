"""Verdict-level decision with abstention.

The classifier gives probabilities over items. Instead of abstaining on item confidence,
we marginalise to the city's verdict: P(accept) = sum of item probabilities the city accepts.
Two items that share a verdict therefore do not cause needless abstention, while an item
split across 'accept' and 'reject' items does.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rules import CityRules


@dataclass(frozen=True)
class Decision:
    verdict: str  # accept | reject | not_sure
    p_accept: float
    p_reject: float
    p_conditional: float
    top_item: str
    top_item_p: float
    note: str
    source_url: str


def decide(probs: dict[str, float], city: CityRules, threshold: float = 0.85) -> Decision:
    total = sum(probs.values())
    if total <= 0 or any(p < 0 for p in probs.values()):
        raise ValueError("probabilities must be non-negative with positive sum")
    probs = {k: v / total for k, v in probs.items()}
    unknown = set(probs) - set(city.rules)
    if unknown:
        raise ValueError(f"unknown items: {sorted(unknown)}")
    mass = {"accept": 0.0, "reject": 0.0, "conditional": 0.0}
    for item, p in probs.items():
        mass[city.rules[item].verdict] += p
    top = max(probs, key=probs.get)
    rule = city.rules[top]
    if mass["accept"] >= threshold:
        verdict = "accept"
    elif mass["reject"] >= threshold:
        verdict = "reject"
    else:
        verdict = "not_sure"
    return Decision(verdict, mass["accept"], mass["reject"], mass["conditional"],
                    top, probs[top], rule.note, city.sources[rule.source].url)
