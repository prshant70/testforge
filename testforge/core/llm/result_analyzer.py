"""Analyze simulated execution results into a user-facing validation report."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List

from testforge.core.executor.validator import ExecutionResult
from testforge.core.llm.validation_planner import ValidationPlan
from testforge.core.llm.guard import llm_disabled


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


def _deterministic_regressions_from_checks(execution_result: ExecutionResult) -> tuple[list[str], list[str]]:
    fails: list[str] = []
    warns: list[str] = []
    for a in execution_result.artifacts:
        if a.get("type") != "check":
            continue
        status = a.get("status")
        title = str(a.get("title") or "").strip()
        details = str(a.get("details") or "").strip()
        fp = a.get("file")
        prefix = f"{fp}: " if fp else ""
        if status == "fail":
            fails.append(f"{prefix}{title} — {details}")
        elif status == "warn":
            warns.append(f"{prefix}{title} — {details}")
    return fails, warns


def _try_parse_json(text: str) -> dict | None:
    t = (text or "").strip()
    if not t:
        return None
    # Direct parse
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    # Try to extract the first JSON object block
    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def analyze_results(
    execution_result: ExecutionResult,
    validation_plan: ValidationPlan,
    *,
    config: dict,
) -> ValidationReport:
    if llm_disabled() or not str(config.get("llm_api_key") or "").strip():
        # Deterministic report based on built-in checks.
        fails, warns = _deterministic_regressions_from_checks(execution_result)
        pytest_targets: list[str] = []
        for a in execution_result.artifacts:
            if a.get("type") == "pytest" and isinstance(a.get("targets"), list):
                pytest_targets = [str(x) for x in a.get("targets") if str(x).strip()]
                break

        if fails:
            summary = "Deterministic validations found issues. Fix these before merging."
            if pytest_targets:
                summary += "\n\nSelected pytest targets (not executed):\n- " + "\n- ".join(pytest_targets[:25])
            return ValidationReport(regressions=fails[:10], summary=summary)

        summary = "Simulated validation completed. No deterministic issues detected."
        if warns:
            summary += " Warnings were found; consider follow-ups:\n- " + "\n- ".join(warns[:5])
        if pytest_targets:
            summary += "\n\nSelected pytest targets (not executed):\n- " + "\n- ".join(pytest_targets[:25])
        summary += "\nEnable an API key for LLM-based deeper analysis."
        return ValidationReport(regressions=[], summary=summary)

    from testforge.core.llm._openai_tools import run_with_tools

    system = (
        "You analyze change validation results. "
        "Return ONLY valid JSON (no markdown, no prose): "
        "{\"regressions\": [\"...\"], \"summary\": \"...\"}. "
        "Be conservative: if uncertain, suggest follow-up validations instead of claiming regressions."
    )
    user = (
        "Validation plan:\n"
        + getattr(validation_plan, "raw_output", "")
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
        purpose="analyze validation execution results",
        max_tool_rounds=1,
        temperature=0.2,
    )
    data = _try_parse_json(text)
    if data is None:
        # One strict retry: ask the model to re-emit valid JSON only.
        retry = run_with_tools(
            config=config,
            system="Return ONLY valid JSON. No markdown. No extra keys.",
            user=(
                "Reformat the following into valid JSON with keys "
                "\"regressions\" (array of strings) and \"summary\" (string):\n\n"
                + text
            ),
            tools=[],
            purpose="repair malformed result JSON",
            max_tool_rounds=1,
            temperature=0.0,
        )
        data = _try_parse_json(retry)

    if data is not None:
        reg = data.get("regressions") or []
        summ = data.get("summary") or ""
        if isinstance(reg, list) and isinstance(summ, str):
            reg2 = [str(x).strip() for x in reg if str(x).strip()]
            return ValidationReport(regressions=reg2[:10], summary=summ.strip())

    # Fallback: never lose deterministic signal just because the LLM output was malformed.
    fails, warns = _deterministic_regressions_from_checks(execution_result)
    if fails:
        return ValidationReport(
            regressions=fails[:10],
            summary="LLM output was malformed; reporting deterministic validation failures instead.",
        )
    summary = "Could not parse LLM output; no deterministic regressions detected."
    if warns:
        summary += " Warnings were found; consider follow-ups:\n- " + "\n- ".join(warns[:5])
    return ValidationReport(regressions=[], summary=summary)

