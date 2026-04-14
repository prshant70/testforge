"""Analyze simulated execution results into a user-facing validation report."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from testforge.core.executor.validator import ExecutionResult
from testforge.core.llm.validation_planner import ValidationPlan


@dataclass
class ValidationReport:
    regressions: List[str]
    summary: str

    def _display_lines(self) -> list[str]:
        out: list[str] = []
        out.append("⚙️ Running validations...\n")
        if self.regressions:
            out.append("❌ Regression detected:")
            for r in self.regressions:
                out.append(f"- {r}")
        else:
            out.append("✅ No obvious regressions detected (simulated).")
        out.append("")
        out.append(self.summary.strip())
        return out


def analyze_results(
    execution_result: ExecutionResult,
    validation_plan: ValidationPlan,
    *,
    config: dict,
) -> ValidationReport:
    if not str(config.get("llm_api_key") or "").strip():
        # Deterministic, minimal summary: no LLM reasoning.
        summary = (
            "Simulated validation completed. "
            "Enable `--run` with an API key for deeper analysis."
        )
        return ValidationReport(regressions=[], summary=summary)

    from testforge.core.llm._openai_tools import run_with_tools

    system = (
        "You analyze change validation results. "
        "Return ONLY JSON: {\"regressions\": [\"...\"], \"summary\": \"...\"}. "
        "Be conservative: if uncertain, suggest follow-up validations instead of claiming regressions."
    )
    user = (
        "Validation scenarios:\n"
        + "\n".join(f"- {s}" for s in validation_plan.scenarios)
        + "\n\nExecution observations:\n"
        + "\n".join(f"- {o}" for o in execution_result.observations)
        + "\n\nArtifacts (truncated):\n"
        + json.dumps(execution_result.artifacts[:6], ensure_ascii=False)[:6000]
    )

    text = run_with_tools(
        config=config,
        system=system,
        user=user,
        tools=[],
        max_tool_rounds=1,
        temperature=0.2,
    )
    try:
        data = json.loads(text)
        reg = data.get("regressions") or []
        summ = data.get("summary") or ""
        if isinstance(reg, list) and isinstance(summ, str):
            reg2 = [str(x).strip() for x in reg if str(x).strip()]
            return ValidationReport(regressions=reg2[:10], summary=summ.strip())
    except Exception:
        pass
    return ValidationReport(regressions=[], summary="Could not parse LLM output; no regressions flagged.")

