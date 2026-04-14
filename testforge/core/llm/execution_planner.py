"""Plan lightweight validation execution steps using tools (bounded)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from testforge.core.llm.validation_planner import ValidationPlan
from testforge.core.tools.code_tools import CodeTools


@dataclass
class ExecutionPlan:
    steps: List[Dict]


def plan_execution(validation_plan: ValidationPlan, tools: CodeTools, *, config: dict) -> ExecutionPlan:
    """
    Produce a short tool-grounded execution plan.

    If API key missing, return a deterministic plan that uses only `get_diff`
    and simple `read_file` for changed files (executed by the executor).
    """
    if not str(config.get("llm_api_key") or "").strip():
        return ExecutionPlan(
            steps=[
                {"action": "inspect_diff", "tool": "get_diff"},
                {"action": "list_files", "tool": "list_files", "args": {"limit": 200}},
                {"action": "summarize_expected_behavior", "input": validation_plan.scenarios[:5]},
            ],
        )

    from testforge.core.llm._openai_tools import ToolSpec, run_with_tools

    tool_specs = [
        ToolSpec(
            name="get_diff",
            description="Return the full git diff text for base...feature.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda: tools.get_diff(),
        ),
        ToolSpec(
            name="search_code",
            description="Naive substring search across repo. Returns matching file paths.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=lambda query: tools.search_code(query),
        ),
        ToolSpec(
            name="read_file",
            description="Read a file (path relative to repo root).",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=lambda path: tools.read_file(path),
        ),
        ToolSpec(
            name="list_files",
            description="List repository files (optionally filtered by suffix).",
            parameters={
                "type": "object",
                "properties": {
                    "suffix": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
            handler=lambda suffix=None, limit=200: tools.list_files(suffix=suffix, limit=limit),
        ),
    ]

    system = (
        "You plan a small set of deterministic validation steps. "
        "You MUST use tools to ground the plan. "
        "Return ONLY JSON: {\"steps\": [{\"tool\": \"...\", \"args\": {...}, \"purpose\": \"...\"}, ...]} "
        "Keep steps <= 8."
    )
    user = (
        "Validation scenarios:\n"
        + "\n".join(f"- {s}" for s in validation_plan.scenarios)
        + "\n\nCreate an execution plan. Use tools like get_diff, list_files, read_file as needed."
    )

    text = run_with_tools(
        config=config,
        system=system,
        user=user,
        tools=tool_specs,
        max_tool_rounds=4,
        temperature=0.2,
    )
    try:
        data = json.loads(text)
        steps = data.get("steps") or []
        if isinstance(steps, list):
            return ExecutionPlan(steps=steps[:10])
    except Exception:
        pass
    return ExecutionPlan(steps=[{"tool": "get_diff", "args": {}, "purpose": "fallback"}])

