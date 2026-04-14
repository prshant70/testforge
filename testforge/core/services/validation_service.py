"""Change-aware validation service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext
from testforge.core.models.requests import ValidateRequest
from testforge.core.validator import resolve_git_sha, validate_git_branch, validate_path_exists

from testforge.core.analyzer.change_analyzer import ChangeSummary, analyze_changes
from testforge.core.analyzer.impact_mapper import map_impact
from testforge.core.analyzer.risk_classifier import RiskSummary, classify_risk
from testforge.core.executor.validator import execute_validation
from testforge.core.llm.execution_planner import plan_execution
from testforge.core.llm.result_analyzer import ValidationReport, analyze_results
from testforge.core.llm.validation_planner import ValidationPlan, generate_validation_plan
from testforge.core.tools.code_tools import CodeTools
from testforge.core.cache.store import get_repo_id, read_cache, write_cache


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

        base_sha = resolve_git_sha(self._resolved_base, repo=self._repo)
        feature_sha = resolve_git_sha(self._resolved_feature, repo=self._repo)
        repo_id = get_repo_id(self._repo)

        cached_change = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="change_summary",
        )
        if cached_change:
            self.logger.info("Cache hit: change_summary (%s..%s)", base_sha[:8], feature_sha[:8])
            change_summary = ChangeSummary(
                files=list(cached_change.get("files", [])),
                functions=list(cached_change.get("functions", [])),
                diff_text=str(cached_change.get("diff_text", "")),
            )
        else:
            self.logger.info("Cache miss: change_summary (%s..%s)", base_sha[:8], feature_sha[:8])
            change_summary = analyze_changes(
                self._resolved_base,
                self._resolved_feature,
                repo_path=str(self._repo),
            )
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="change_summary",
                    value={
                        "files": change_summary.files,
                        "functions": change_summary.functions,
                        "diff_text": change_summary.diff_text,
                    },
                )

        cached_risk = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="risk_summary",
        )
        if cached_risk:
            risk = RiskSummary(
                level=str(cached_risk.get("level", "low")),
                types=list(cached_risk.get("types", [])),
            )
        else:
            risk = classify_risk(change_summary)
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="risk_summary",
                    value={"level": risk.level, "types": risk.types},
                )

        tools = CodeTools(
            repo_path=self._repo,
            base=self._resolved_base,
            feature=self._resolved_feature,
            diff_text=change_summary.diff_text,
            changed_files=change_summary.files,
            config=dict(self.config),
        )

        cached_impact = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="impact_summary",
        )
        if cached_impact:
            impact = type("ImpactSummaryObj", (), cached_impact)()
            impact.endpoints = cached_impact.get("endpoints", [])
            impact.mapping = cached_impact.get("mapping", {})
        else:
            impact = map_impact(change_summary, tools)
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="impact_summary",
                    value={"endpoints": impact.endpoints, "mapping": impact.mapping},
                )

        cached_plan = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="validation_plan",
        )
        if cached_plan:
            plan = ValidationPlan(scenarios=cached_plan.get("scenarios", []))
        else:
            plan = generate_validation_plan(change_summary, impact, risk, config=dict(self.config))
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="validation_plan",
                    value={"scenarios": plan.scenarios},
                )

        # Attach summaries for CLI rendering (v1 convenience).
        plan._change_summary = change_summary  # type: ignore[attr-defined]
        plan._impact_summary = impact  # type: ignore[attr-defined]
        plan._risk_summary = risk  # type: ignore[attr-defined]

        if not request.run:
            return plan

        cached_report = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="validation_report",
        )
        if cached_report:
            return ValidationReport(
                regressions=cached_report.get("regressions", []),
                summary=cached_report.get("summary", ""),
            )

        exec_plan = plan_execution(plan, tools, config=dict(self.config))
        result = execute_validation(exec_plan, tools)
        report = analyze_results(result, plan, config=dict(self.config))
        if not request.nocache:
            write_cache(
                repo_id=repo_id,
                base_sha=base_sha,
                feature_sha=feature_sha,
                key="validation_report",
                value={"regressions": report.regressions, "summary": report.summary},
            )
        return report
