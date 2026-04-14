"""LLM-backed validation planner (structured text output + safety fallback)."""

from __future__ import annotations

from dataclasses import dataclass

from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.impact_mapper import ImpactSummary
from testforge.core.analyzer.risk_classifier import RiskSummary
from testforge.core.llm.guard import llm_disabled


SYSTEM_PROMPT = """
You are a senior backend engineer reviewing a production code change before merge.

Your goal is to produce a decisive validation report.

You MUST:
1. Explain behavioral impact clearly
2. Identify specific regression scenarios
3. Describe observable failure modes (what will break and how it will appear)
4. Prioritize risks (HIGH / MEDIUM / LOW)
5. Recommend the most critical validations (4–5 only)
6. Provide a clear merge risk decision

STRICT RULES:

- Do NOT use vague phrases like:
  "may cause issues", "might fail", "could lead to problems"

- ALWAYS describe failure in observable terms:
  Examples:
  - "returns 500 instead of 400"
  - "incorrect order status returned"
  - "request routed to wrong handler"

- ALWAYS include at least one HIGH risk regression with a concrete failure mode

- Keep output concise but high signal

- Do NOT include instructions, rules, or explanations in the output

- Do NOT repeat template text like "Rules:"

Think like a senior engineer deciding whether to approve or block a PR.
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

1. Describe behavioral impact (what changed in system behavior)
2. Identify concrete regression risks with failure modes
3. Classify risks into HIGH / MEDIUM / LOW
4. Suggest 4–5 targeted validations

Output format:

---
🔍 Behavioral Impact:
<clear behavior explanation>

💥 Potential Regressions:

🔥 HIGH RISK:
- <specific regression + observable failure>

⚠️ MEDIUM RISK:
- <specific issue>

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
- ALWAYS include at least one concrete failure mode
- ALWAYS produce 4 or 5 validations (not fewer)
- Each validation MUST include expected outcome
- Do NOT include "Rules:" in output
- Do NOT repeat instructions
"""

def sanitize_output(text: str) -> str:
    # Remove accidental prompt leakage
    text = (text or "")
    text = text.replace("RULES:", "")
    text = text.replace("Rules:", "")
    text = text.replace("Your task:", "")

    # Remove extra blank sections
    return text.strip()


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
    user = build_validation_prompt(change_summary, impact_summary, risk_summary) + "\n" + failure_hint

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
    if not out or not _looks_like_decision_report(out):
        return _fallback_plan()
    return ValidationPlan(raw_output=out)

