"""LLM-backed validation planner (structured text output + safety fallback)."""

from __future__ import annotations

from dataclasses import dataclass

from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.impact_mapper import ImpactSummary
from testforge.core.analyzer.confidence_scorer import ConfidenceSummary
from testforge.core.analyzer.intent_classifier import IntentSummary
from testforge.core.analyzer.risk_classifier import RiskSummary
from testforge.core.llm.guard import llm_disabled


SYSTEM_PROMPT = """
You are a senior backend engineer reviewing a production code change.

Your goal is to produce a precise, evidence-based validation report.

---

CORE RESPONSIBILITIES:

1. Explain behavioral impact (what changed in system behavior)
2. Identify risks introduced by the change (NOT hypothetical failures)
3. Respect change intent:
   - If INTENTIONAL → do NOT treat expected behavior as regression
4. Recommend high-signal validations
5. Provide merge risk decision

---

RISK DEFINITION (CRITICAL):

A risk must be directly supported by the code change.

DO:
- Identify changed components (methods, fields, logic)
- Describe how behavior or dependency has changed
- Highlight new assumptions or dependencies

DO NOT:
- speculate about failures
- use "if this fails then X happens"
- assume downstream systems break without evidence

---

STRICT LANGUAGE RULES:

NEVER use:
- "if this fails"
- "could lead to"
- "might cause"
- "would result in"

INSTEAD use:
- "introduces dependency on"
- "changes behavior of"
- "adds requirement for"
- "alters handling of"

---

OUTPUT QUALITY:

- Every risk MUST reference a change
- No generic statements
- No hypothetical chains
- Be concise and high signal
"""


@dataclass
class ValidationPlan:
    raw_output: str


def build_validation_prompt(change_summary, impact_summary, risk_summary, intent_summary, confidence_summary) -> str:
    return f"""
Code Changes Summary:
{change_summary}

Impacted Endpoints:
{impact_summary.endpoints}

Risk Types:
{risk_summary.types}

Intent Assessment:
- intent_label: {intent_summary.intent_label}
- intent_score: {intent_summary.intent_score}
- signals: {intent_summary.signals}

Analysis Confidence:
- level: {confidence_summary.level}
- score: {confidence_summary.score}
- reasons: {confidence_summary.reasons}

IMPORTANT:

Only include risks that are directly supported by the code change.

For each risk:
- mention the changed component
- describe the concrete impact

Avoid:
- hypothetical failure chains
- "if this fails" reasoning
- generic downstream breakage

Use confidence level to adjust tone:

- High confidence:
  → be assertive and decisive

- Medium:
  → be balanced

- Low:
  → be cautious, avoid strong claims

Your task:

1. Describe behavioral impact (what changed in system behavior)
2. Identify concrete regression risks with failure modes
3. Classify risks into HIGH / MEDIUM / LOW
4. Suggest 4–5 targeted validations

Output format:

---
🧭 Change Intent:
{intent_summary.intent_label} ({intent_summary.intent_score})

🔍 Behavioral Impact:
<clear behavior explanation>

💥 Change-Induced Risks:

🔥 HIGH RISK:
- Change: <component>
  Impact: <behavior/dependency change>

⚠️ MEDIUM RISK:
- Change: <component>
  Impact: <behavior/dependency change>

💡 LOW RISK:
- <edge case>

🧪 Suggested Validations:

🔥 1. <critical scenario>
   → Expect: <explicit outcome>

🔥 2. ...
   → Expect: ...

⚠️ 3. ...
   → Expect: ...

⚠️ 4. ...
   → Expect: ...

💡 5. ...
   → Expect: ...

🚨 Merge Risk:
<LOW / MEDIUM / HIGH>

RULES:
- No speculative language
- No "if this fails"
- Always anchor risks to code changes
- Max 5 validations
"""

def sanitize_output(text: str) -> str:
    banned_phrases = [
        "if this fails",
        "could lead to",
        "might cause",
        "would result in",
    ]

    lines = (text or "").split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        low = line.lower()
        if any(phrase in low for phrase in banned_phrases):
            continue
        # Remove accidental prompt leakage
        if low.strip() in {"rules:", "rules", "your task:", "your task"}:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _looks_like_decision_report(text: str) -> bool:
    t = (text or "").lower()
    if "behavioral impact" not in t:
        return False
    if "high risk" not in t:
        return False
    if "merge risk" not in t:
        return False
    if "→ expect:" not in t:
        return False
    if "change-induced risks" not in t:
        return False
    return True


def _fallback_plan() -> ValidationPlan:
    return ValidationPlan(
        raw_output=(
            "⚠️ Unable to generate detailed validation plan.\n\n"
            "Basic suggestion:\n"
            "- Verify impacted endpoints manually"
        ),
    )


def generate_validation_plan(
    change_summary: ChangeSummary,
    impact_summary: ImpactSummary,
    risk_summary: RiskSummary,
    intent_summary: IntentSummary,
    confidence_summary: ConfidenceSummary,
    *,
    config: dict,
) -> ValidationPlan:
    """
    Produce a structured, prioritized, regression-focused plan as text.
    """
    if llm_disabled() or not str(config.get("llm_api_key") or "").strip():
        return _fallback_plan()

    from testforge.core.llm._openai_tools import run_with_tools

    failure_hint = """
Important:
Describe at least one regression as a concrete failure observable by API users.
"""
    user = build_validation_prompt(
        change_summary,
        impact_summary,
        risk_summary,
        intent_summary,
        confidence_summary,
    ) + "\n" + failure_hint

    text = run_with_tools(
        config=config,
        system=SYSTEM_PROMPT,
        user=user,
        tools=[],
        purpose="generate validation plan (behavior + regressions + validations)",
        max_tool_rounds=1,
        temperature=0.2,
    )

    out = sanitize_output(text)

    # Optional safety downgrade: in the risk section, drop lines not anchored to Change/Impact.
    filtered: list[str] = []
    in_risk_section = False
    for line in out.splitlines():
        low = line.lower().strip()
        if low.startswith("💥 change-induced risks"):
            in_risk_section = True
            filtered.append(line)
            continue
        if in_risk_section and low.startswith("🧪 suggested validations"):
            in_risk_section = False
            filtered.append(line)
            continue
        if in_risk_section:
            if not low or low.startswith(("🔥", "⚠️", "💡")):
                filtered.append(line)
                continue
            if ("change:" in low) or ("impact:" in low):
                filtered.append(line)
                continue
            continue
        filtered.append(line)

    out = "\n".join(filtered).strip()
    if not out or not _looks_like_decision_report(out):
        return _fallback_plan()

    # Safety rule: when intent is intentional, avoid calling obvious changes "regressions".
    if intent_summary.intent_label == "intentional":
        out = out.replace("regression", "expected behavior change")
        out = out.replace("Regression", "Expected behavior change")

    return ValidationPlan(raw_output=out)

