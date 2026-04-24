"""Lightweight intent scoring: intentional change vs unintended regression."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class IntentSummary:
    intent_score: float  # 0.0 - 1.0
    intent_label: str  # "intentional" | "mixed" | "uncertain"
    signals: List[str]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _label(score: float) -> str:
    if score >= 0.65:
        return "intentional"
    if score >= 0.4:
        return "mixed"
    return "uncertain"


def _iter_diff_lines(diff_text: str) -> tuple[list[str], list[str]]:
    added: list[str] = []
    removed: list[str] = []
    for line in (diff_text or "").splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") and not line.startswith("++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("--"):
            removed.append(line[1:])
    return added, removed


def _git_last_commit_message(repo: Path, ref: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", ref],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except Exception:
        pass
    return ""


def classify_intent(
    change_summary,
    *,
    repo_path: Optional[str] = None,
    feature_ref: Optional[str] = None,
) -> IntentSummary:
    """
    Deterministic, rule-based intent scoring.

    Uses diff text and (optionally) last commit message on feature ref.
    """
    diff = change_summary.diff_text or ""
    files = getattr(change_summary, "files", []) or []

    added, removed = _iter_diff_lines(diff)
    added_text = "\n".join(added).lower()
    removed_text = "\n".join(removed).lower()

    score = 0.5
    signals: list[str] = []

    # Positive signals
    new_endpoint = any(
        re.search(r"(@app\.)|(router\.)", ln) for ln in added
    )
    if new_endpoint:
        score += 0.3
        signals.append("new endpoint/route added")

    validation_added = (
        "raise badrequest" in added_text
        or "raise " in added_text
        or "if not" in added_text
        or " is none" in added_text
    )
    if validation_added:
        score += 0.25
        signals.append("validation added/strengthened")

    feature_flag = any(k in added_text for k in ("enabled", "feature", "flag"))
    if feature_flag:
        score += 0.2
        signals.append("feature/config flag signal")

    # Negative signals
    deletion = len(removed) > 0
    if deletion:
        score -= 0.3
        signals.append("deletions present")

    condition_changed = ("if " in added_text) and ("if " in removed_text)
    if condition_changed:
        score -= 0.25
        signals.append("condition logic modified")

    return_changed = ("return" in added_text) and ("return" in removed_text)
    if return_changed:
        score -= 0.2
        signals.append("return value/shape modified")

    # File-path hints: migrations/config changes are often intentional.
    if any(f.endswith((".sql", ".json", ".yaml", ".yml")) for f in files):
        score += 0.1
        signals.append("config/migration touched")

    # Optional commit message signal
    repo = Path(repo_path).expanduser().resolve() if repo_path else None
    ref = feature_ref or "HEAD"
    msg = _git_last_commit_message(repo, ref) if repo else ""
    mlow = msg.lower()
    if mlow:
        if any(w in mlow for w in ("add", "introduce")):
            score += 0.1
            signals.append("commit message suggests intentional addition")
        if "fix" in mlow:
            score -= 0.05
            signals.append("commit message suggests bugfix (risk of regression)")

    score = _clamp(score)
    return IntentSummary(intent_score=score, intent_label=_label(score), signals=signals)

