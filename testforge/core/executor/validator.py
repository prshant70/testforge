"""Execute a lightweight validation plan (v1 simulated mode)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from testforge.core.llm.execution_planner import ExecutionPlan
from testforge.core.tools.code_tools import CodeTools


@dataclass
class ExecutionResult:
    observations: List[str]
    artifacts: List[Dict[str, Any]]


def _check(status: str, title: str, details: str, *, file: str | None = None) -> dict[str, Any]:
    return {"type": "check", "status": status, "title": title, "details": details, "file": file}


def _extract_candidate_paths(diff_text: str) -> list[str]:
    """
    Extract path-like tokens from a diff that might refer to repo files.
    This is intentionally heuristic and language-agnostic.
    """
    out: list[str] = []
    seen: set[str] = set()

    # diff headers: diff --git a/foo b/foo
    for m in re.finditer(r"^diff --git a/([^\s]+) b/[^\s]+$", diff_text, re.M):
        p = m.group(1).strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)

    # quoted or bare file paths in lines (e.g. 'config_template.json', "app/constants/encryption.py")
    for m in re.finditer(r"(?P<q>['\"])?(?P<p>[A-Za-z0-9_./-]+\.(py|js|ts|tsx|json|ya?ml|sql))(?P=q)?", diff_text):
        p = m.group("p")
        if p and p not in seen:
            seen.add(p)
            out.append(p)

    return out[:200]


def _deterministic_validations(tools: CodeTools) -> list[dict[str, Any]]:
    """
    Run a small set of safe, deterministic validations that do not require
    heavy infra (DB, network, service runtime).
    """
    checks: list[dict[str, Any]] = []

    # 1) Basic: changed files exist in feature ref (or report deletion/rename).
    for fp in tools.changed_files[:200]:
        content = tools.git_show(ref=tools.feature, path=fp)
        if content.startswith("ERROR: git show failed"):
            # Could be deleted/renamed; treat as warning not failure.
            checks.append(
                _check(
                    "warn",
                    "file missing at feature ref",
                    f"{fp} not readable at {tools.feature} (may be deleted/renamed).",
                    file=fp,
                ),
            )
        else:
            checks.append(_check("pass", "file readable at feature ref", fp, file=fp))

    # 2) Parse config-like files (JSON/YAML) changed in this diff.
    for fp in tools.changed_files:
        if fp.endswith(".json"):
            raw = tools.git_show(ref=tools.feature, path=fp)
            if raw.startswith("ERROR:"):
                continue
            try:
                json.loads(raw)
                checks.append(_check("pass", "valid json", f"{fp} parses as JSON", file=fp))
            except Exception as exc:
                checks.append(_check("fail", "invalid json", f"{fp} failed to parse: {exc}", file=fp))
        if fp.endswith(".yaml") or fp.endswith(".yml"):
            raw = tools.git_show(ref=tools.feature, path=fp)
            if raw.startswith("ERROR:"):
                continue
            try:
                import yaml  # PyYAML is already a dependency

                yaml.safe_load(raw)
                checks.append(_check("pass", "valid yaml", f"{fp} parses as YAML", file=fp))
            except Exception as exc:
                checks.append(_check("fail", "invalid yaml", f"{fp} failed to parse: {exc}", file=fp))

    # 3) Python syntax check for changed .py files (only syntax; no imports/runtime).
    for fp in tools.changed_files:
        if not fp.endswith(".py"):
            continue
        raw = tools.git_show(ref=tools.feature, path=fp)
        if raw.startswith("ERROR:"):
            continue
        try:
            compile(raw, fp, "exec")
            checks.append(_check("pass", "python syntax ok", fp, file=fp))
        except SyntaxError as exc:
            checks.append(
                _check(
                    "fail",
                    "python syntax error",
                    f"{fp}:{exc.lineno}:{exc.offset} {exc.msg}",
                    file=fp,
                ),
            )

    # 4) SQL sanity: non-empty + contains at least one likely statement keyword.
    for fp in tools.changed_files:
        if not fp.endswith(".sql"):
            continue
        raw = tools.git_show(ref=tools.feature, path=fp)
        if raw.startswith("ERROR:"):
            continue
        text = raw.strip().lower()
        if not text:
            checks.append(_check("fail", "empty sql file", fp, file=fp))
            continue
        if not re.search(r"\b(create|alter|drop|insert|update|delete|select)\b", text):
            checks.append(_check("warn", "sql looks unusual", f"{fp} has no obvious SQL statements", file=fp))
        else:
            checks.append(_check("pass", "sql sanity ok", fp, file=fp))

    # 5) Referenced-path existence: if diff mentions a file, ensure it exists at feature ref.
    for fp in _extract_candidate_paths(tools.diff_text):
        raw = tools.git_show(ref=tools.feature, path=fp)
        if raw.startswith("ERROR:"):
            checks.append(_check("warn", "referenced file missing", f"Diff references {fp} but it is not readable at {tools.feature}", file=fp))
        else:
            checks.append(_check("pass", "referenced file readable", fp, file=fp))

    return checks


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

    det = _deterministic_validations(tools)
    artifacts.extend(det)
    failed = [c for c in det if c.get("status") == "fail"]
    warned = [c for c in det if c.get("status") == "warn"]
    obs.append(f"deterministic checks: {len(det)} run, {len(failed)} failed, {len(warned)} warnings")

    return ExecutionResult(observations=obs, artifacts=artifacts)

