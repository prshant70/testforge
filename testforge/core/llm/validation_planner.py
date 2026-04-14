"""LLM-backed validation planner (structured text output + safety fallback)."""

from __future__ import annotations

from dataclasses import dataclass

from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.impact_mapper import ImpactSummary
from testforge.core.analyzer.risk_classifier import RiskSummary
from testforge.core.llm.guard import llm_disabled


SYSTEM_PROMPT = """
You are a senior backend engineer reviewing a code change.

Your goal is NOT to list generic test cases.

Your goal is to:
1. Understand what changed
2. Identify what behavior might break
3. Prioritize the highest risk issues
4. Suggest only the most important validations

Be precise, practical, and concise.

Focus on:
- behavior changes
- edge cases introduced by the change
- error handling differences
- downstream dependency impact

Avoid generic suggestions.
Avoid repeating obvious validations unless they are at risk.

Always highlight at least one likely regression if possible.

Think like someone reviewing a PR before merging to production.
"""


@dataclass
class ValidationPlan:
    raw_output: str


def build_validation_prompt(change_summary, impact_summary, risk_summary) -> str:
    return f"""
Code Changes Summary:
{change_summary}

Impacted Endpoints:
{impact_summary.endpoints}

Risk Types:
{risk_summary.types}

Your task:

1. Explain WHAT changed in behavior (not code diff, but behavior impact)
2. Identify WHAT might break (regression hypotheses)
3. Classify risks into:
   - HIGH (very likely to break)
   - MEDIUM (possible issue)
   - LOW (edge cases)
4. Suggest a SMALL set of targeted validations (max 5)

Output format:

---
🔍 Behavioral Impact:
<short explanation>

💥 Potential Regressions:

🔥 HIGH RISK:
- ...

⚠️ MEDIUM RISK:
- ...

💡 LOW RISK:
- ...

🧪 Suggested Validations:
1. <scenario + expected behavior>
2. ...

Rules:
- Be specific to the endpoint
- Include expected outcomes (status code, behavior)
- Do NOT generate more than 5 validations
- Prioritize signal over completeness
"""


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
    *,
    config: dict,
) -> ValidationPlan:
    """
    Produce a structured, prioritized, regression-focused plan as text.
    """
    if llm_disabled() or not str(config.get("llm_api_key") or "").strip():
        return _fallback_plan()

    from testforge.core.llm._openai_tools import run_with_tools

    user = build_validation_prompt(change_summary, impact_summary, risk_summary)

    text = run_with_tools(
        config=config,
        system=SYSTEM_PROMPT,
        user=user,
        tools=[],
        purpose="generate validation plan (behavior + regressions + validations)",
        max_tool_rounds=1,
        temperature=0.2,
    )

    out = (text or "").strip()
    if not out:
        return _fallback_plan()
    return ValidationPlan(raw_output=out)

