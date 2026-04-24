"""Deterministic confidence scoring for validation analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class ConfidenceSummary:
    score: float  # 0.0 - 1.0
    level: str  # "High" | "Medium" | "Low"
    reasons: List[str]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _level(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def _added_lines(diff_text: str) -> list[str]:
    out: list[str] = []
    for line in (diff_text or "").splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+") and not line.startswith("++"):
            out.append(line[1:])
    return out


def compute_confidence(change_summary, intent_summary) -> ConfidenceSummary:
    """
    Compute an explainable confidence score for the analysis.

    Deterministic-first: uses only diff text, file count, and intent score.
    """
    score = 0.5
    reasons: list[str] = []

    diff = getattr(change_summary, "diff_text", "") or ""
    files = getattr(change_summary, "files", []) or []

    added = "\n".join(_added_lines(diff))
    added_low = added.lower()

    # 1) Clear structural change
    structural = (
        ("class " in added)
        or ("field(" in added_low)
        or ("column(" in added_low)
        or ("encryptedjsonfield" in added_low)
        or re.search(r"(@app\.)|(router\.)", added) is not None
    )
    if structural:
        score += 0.25
        reasons.append("Clear structural change detected")

    # 2) High intent score
    if float(getattr(intent_summary, "intent_score", 0.5)) >= 0.65:
        score += 0.2
        reasons.append("Strong intent signals present")

    # 3) Localized change
    if len(files) <= 3:
        score += 0.15
        reasons.append("Change is localized")

    # 4) Large diff
    if len(files) > 8:
        score -= 0.25
        reasons.append("Large multi-file change reduces certainty")

    # 5) Weak intent
    if float(getattr(intent_summary, "intent_score", 0.5)) < 0.4:
        score -= 0.2
        reasons.append("Weak or unclear intent signals")

    # 6) Indirect impact heuristic
    if "manager" in (diff or "").lower():
        score -= 0.1
        reasons.append("Indirect dependencies increase uncertainty")

    score = _clamp(score)
    level = _level(score)

    if not reasons:
        reasons.append("Limited explicit signals; baseline heuristic used")

    return ConfidenceSummary(score=score, level=level, reasons=reasons)

