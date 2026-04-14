"""Cheap risk classification heuristics based on diff text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from testforge.core.analyzer.change_analyzer import ChangeSummary


@dataclass
class RiskSummary:
    level: str  # low, medium, high
    types: List[str]


def classify_risk(change_summary: ChangeSummary) -> RiskSummary:
    diff = change_summary.diff_text.lower()

    types: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        if t not in seen:
            seen.add(t)
            types.append(t)

    if "validation" in diff or "validator" in diff:
        add("validation change")
    if "try:" in diff or "except" in diff or "try {" in diff or "catch" in diff or "throw " in diff:
        add("error handling change")
    if "db" in diff or "session" in diff or "transaction" in diff or "orm" in diff or "sql" in diff:
        add("data persistence change")
    if "http" in diff or "fetch(" in diff or "axios" in diff or "requests." in diff or "httpx." in diff:
        add("external call change")

    # Very small v1 heuristic: many changed files or any persistence/errors -> higher.
    level = "low"
    if len(change_summary.files) >= 8:
        level = "high"
    elif len(change_summary.files) >= 3:
        level = "medium"
    if "data persistence change" in types or "error handling change" in types:
        level = "high" if len(change_summary.files) >= 3 else "medium"

    return RiskSummary(level=level, types=types or ["unknown"])

