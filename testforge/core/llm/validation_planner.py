"""LLM-backed validation scenario planner (with deterministic fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.impact_mapper import ImpactSummary
from testforge.core.analyzer.risk_classifier import RiskSummary
from testforge.core.llm.guard import llm_disabled


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
    # Prefer endpoint-targeted checks when available.
    if impact.endpoints:
        ep = impact.endpoints[0]
        scenarios.append(f"{ep}: verify happy-path response shape and status code")
        scenarios.append(f"{ep}: verify invalid payload returns client error (not 500)")
        scenarios.append(f"{ep}: verify missing required fields returns clear validation error")
    if "validation change" in risk.types:
        scenarios.append("input validation: boundary values + empty/null + unexpected types (watch for silent coercion)")
    if "error handling change" in risk.types:
        scenarios.append("error handling: force an exception path and verify error is handled + logged (no crash/no leaked secrets)")
    if "data persistence change" in risk.types:
        scenarios.append("data persistence: verify schema/migration compatibility + write/read + rollback on failure")
    if "external call change" in risk.types:
        scenarios.append("external calls: simulate timeout/5xx and verify retry/fallback/circuit behavior")
    if not scenarios:
        scenarios = [
            "targeted smoke test of the changed user flow (based on diff intent)",
            "run unit tests covering the changed files/modules",
        ]
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
    if llm_disabled() or not str(config.get("llm_api_key") or "").strip():
        return _fallback_plan(risk_summary, impact_summary)

    from testforge.core.llm._openai_tools import run_with_tools

    system = (
        "You are a change-aware validation assistant. "
        "Your job is to surface *implicit* regression risks suggested by the diff, not generic testing advice. "
        "Return ONLY valid JSON: {\"scenarios\": [\"...\"]}. "
        "Rules:\n"
        "- Each scenario MUST be specific to the change (name file/module/endpoint when possible).\n"
        "- Each scenario MUST include an implied risk + a concrete check + an expected failure signal.\n"
        "- Avoid generic items like 'test all endpoints', 'regression test everything', 'ensure works'.\n"
        "- Prefer 6-10 high-signal scenarios over broad coverage.\n"
        "- Keep each scenario to one line."
    )
    user = (
        "Change summary:\n"
        f"- files: {change_summary.files}\n\n"
        "Impacted endpoints:\n"
        f"{impact_summary.endpoints}\n\n"
        "Risk:\n"
        f"- level: {risk_summary.level}\n"
        f"- types: {risk_summary.types}\n\n"
        "Diff (truncated):\n"
        f"{change_summary.diff_text[:6000]}\n\n"
        "Propose 6-10 validation scenarios that target implicit risks in this diff."
    )

    text = run_with_tools(
        config=config,
        system=system,
        user=user,
        tools=[],
        purpose="generate validation scenarios",
        max_tool_rounds=1,
        temperature=0.2,
    )
    # Minimal JSON parse with fallback.
    import json

    try:
        data = json.loads(text)
        scenarios = data.get("scenarios") or []
        if isinstance(scenarios, list) and all(isinstance(x, str) for x in scenarios):
            cleaned: list[str] = []
            for s in scenarios:
                if not isinstance(s, str):
                    continue
                t = s.strip()
                if not t:
                    continue
                # Drop ultra-generic suggestions if the model sneaks them in.
                low = t.lower()
                if "test all endpoints" in low or "regression testing on all endpoints" in low:
                    continue
                cleaned.append(t)
            return ValidationPlan(scenarios=cleaned[:10])
    except Exception:
        pass
    return _fallback_plan(risk_summary, impact_summary)

