"""Execute a lightweight validation plan (v1 simulated mode)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from testforge.core.llm.execution_planner import ExecutionPlan
from testforge.core.tools.code_tools import CodeTools


@dataclass
class ExecutionResult:
    observations: List[str]
    artifacts: List[Dict[str, Any]]


def execute_validation(execution_plan: ExecutionPlan, tools: CodeTools) -> ExecutionResult:
    """
    v1: simulate validations by running tool steps and recording outputs.
    This does NOT run the service or pytest; it produces signals for the LLM.
    """
    obs: list[str] = []
    artifacts: list[dict[str, Any]] = []

    for step in execution_plan.steps:
        tool = step.get("tool") or step.get("action")
        args = step.get("args") or {}
        purpose = step.get("purpose") or step.get("action") or "step"

        if tool == "get_diff":
            out = tools.get_diff()
        elif tool == "search_code":
            out = tools.search_code(**args)
        elif tool == "read_file":
            out = tools.read_file(**args)
        elif tool == "list_files":
            out = tools.list_files(**args)
        elif tool == "git_show":
            out = tools.git_show(**args)
        else:
            out = f"SKIPPED: unknown tool {tool!r}"

        artifacts.append({"tool": tool, "args": args, "purpose": purpose, "output": out})
        if isinstance(out, str):
            obs.append(f"{purpose}: collected {len(out)} chars from {tool}")
        elif isinstance(out, list):
            obs.append(f"{purpose}: {tool} returned {len(out)} items")
        else:
            obs.append(f"{purpose}: {tool} executed")

    return ExecutionResult(observations=obs, artifacts=artifacts)

