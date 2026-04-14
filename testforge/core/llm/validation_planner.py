"""LLM-backed validation scenario planner (with deterministic fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.impact_mapper import ImpactSummary
from testforge.core.analyzer.risk_classifier import RiskSummary


@dataclass
class ValidationPlan:
    scenarios: List[str]

    def _display_lines(self) -> list[str]:
        out: list[str] = []
        out.append("📦 Changed:")
        out.append("- (see below)")  # caller prints change details separately
        out.append("")
        out.append("🧠 Suggested validation:")
        for i, s in enumerate(self.scenarios, 1):
            out.append(f"{i}. {s}")
        return out


def _fallback_plan(risk: RiskSummary, impact: ImpactSummary) -> ValidationPlan:
    scenarios: list[str] = []
    if impact.endpoints:
        scenarios.append(f"happy-path request for {impact.endpoints[0]}")
        scenarios.append(f"invalid input for {impact.endpoints[0]}")
        scenarios.append(f"missing required fields for {impact.endpoints[0]}")
    if "validation change" in risk.types:
        scenarios.append("boundary values and input sanitization checks")
    if "error handling change" in risk.types:
        scenarios.append("simulate dependency failure and confirm stable error response")
    if "data persistence change" in risk.types:
        scenarios.append("verify DB write/read behavior and transaction rollback paths")
    if "external call change" in risk.types:
        scenarios.append("simulate external API timeout/error and verify fallback behavior")
    if not scenarios:
        scenarios = ["run unit tests for changed modules", "run smoke test for main flows"]
    return ValidationPlan(scenarios=scenarios[:8])


def generate_validation_plan(
    change_summary: ChangeSummary,
    impact_summary: ImpactSummary,
    risk_summary: RiskSummary,
    *,
    config: dict,
) -> ValidationPlan:
    """
    Produce a small list of validation scenarios.

    v1 behavior:
    - If API key missing: deterministic fallback.
    - If present: ask LLM for a short scenario list.
    """
    if not str(config.get("llm_api_key") or "").strip():
        return _fallback_plan(risk_summary, impact_summary)

    from testforge.core.llm._openai_tools import run_with_tools

    system = (
        "You are a change-aware validation assistant. "
        "Return ONLY a JSON object like {\"scenarios\": [\"...\"]}. "
        "Keep it short, specific, and actionable."
    )
    user = (
        "Change summary:\n"
        f"- files: {change_summary.files}\n"
        f"- functions: {change_summary.functions}\n\n"
        "Impacted endpoints:\n"
        f"{impact_summary.endpoints}\n\n"
        "Risk:\n"
        f"- level: {risk_summary.level}\n"
        f"- types: {risk_summary.types}\n\n"
        "Propose 5-8 validation scenarios."
    )

    text = run_with_tools(
        config=config,
        system=system,
        user=user,
        tools=[],
        max_tool_rounds=1,
        temperature=0.2,
    )
    # Minimal JSON parse with fallback.
    import json

    try:
        data = json.loads(text)
        scenarios = data.get("scenarios") or []
        if isinstance(scenarios, list) and all(isinstance(x, str) for x in scenarios):
            return ValidationPlan(scenarios=[s.strip() for s in scenarios if s.strip()][:10])
    except Exception:
        pass
    return _fallback_plan(risk_summary, impact_summary)

