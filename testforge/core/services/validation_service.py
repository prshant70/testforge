"""Change-aware validation service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext
from testforge.core.models.requests import ValidateRequest
from testforge.core.validator import validate_git_branch, validate_path_exists

from testforge.core.analyzer.change_analyzer import analyze_changes
from testforge.core.analyzer.impact_mapper import map_impact
from testforge.core.analyzer.risk_classifier import classify_risk
from testforge.core.executor.validator import execute_validation
from testforge.core.llm.execution_planner import plan_execution
from testforge.core.llm.result_analyzer import ValidationReport, analyze_results
from testforge.core.llm.validation_planner import ValidationPlan, generate_validation_plan
from testforge.core.tools.code_tools import CodeTools


class ValidationService:
    """Runs checks to catch regressions between two refs."""

    def __init__(self, ctx: AppContext) -> None:
        self.config = ctx.config
        self.logger = ctx.logger

    def run(self, request: ValidateRequest) -> ValidationPlan | ValidationReport:
        self._validate(request)
        return self._execute(request)

    def _validate(self, request: ValidateRequest) -> None:
        repo: Optional[Path] = None
        if request.path:
            repo = validate_path_exists(request.path, kind="Repository path")
        base = validate_git_branch(request.base, repo=repo)
        feature = validate_git_branch(request.feature, repo=repo)
        self._resolved_base = base
        self._resolved_feature = feature
        self._repo = repo or Path(".").resolve()

    def _execute(self, request: ValidateRequest) -> ValidationPlan | ValidationReport:
        self.logger.info(
            "Analyzing changes between %s and %s",
            self._resolved_base,
            self._resolved_feature,
        )

        change_summary = analyze_changes(
            self._resolved_base,
            self._resolved_feature,
            repo_path=str(self._repo),
        )
        risk = classify_risk(change_summary)

        tools = CodeTools(
            repo_path=self._repo,
            base=self._resolved_base,
            feature=self._resolved_feature,
            diff_text=change_summary.diff_text,
            config=dict(self.config),
        )

        impact = map_impact(change_summary, tools)

        plan = generate_validation_plan(change_summary, impact, risk, config=dict(self.config))

        # Attach summaries for CLI rendering (v1 convenience).
        plan._change_summary = change_summary  # type: ignore[attr-defined]
        plan._impact_summary = impact  # type: ignore[attr-defined]
        plan._risk_summary = risk  # type: ignore[attr-defined]

        if not request.run:
            return plan

        exec_plan = plan_execution(plan, tools, config=dict(self.config))
        result = execute_validation(exec_plan, tools)
        report = analyze_results(result, plan, config=dict(self.config))
        return report
