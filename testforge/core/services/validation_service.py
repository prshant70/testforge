"""Change-aware validation service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext
from testforge.core.models.requests import ValidateRequest
from testforge.core.validator import resolve_git_sha, validate_git_branch, validate_path_exists

from testforge.core.analyzer.change_analyzer import ChangeSummary, analyze_changes
from testforge.core.analyzer.confidence_scorer import ConfidenceSummary, compute_confidence
from testforge.core.analyzer.intent_classifier import IntentSummary, classify_intent
from testforge.core.analyzer.impact_mapper import map_impact
from testforge.core.analyzer.risk_classifier import RiskSummary, classify_risk
from testforge.core.llm.validation_planner import ValidationPlan, generate_validation_plan
from testforge.core.tools.code_tools import CodeTools
from testforge.core.cache.store import get_repo_id, read_cache, write_cache


class ValidationService:
    """Runs checks to catch regressions between two refs."""

    def __init__(self, ctx: AppContext) -> None:
        self.config = ctx.config
        self.logger = ctx.logger

    def run(self, request: ValidateRequest) -> ValidationPlan:
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

    def _execute(self, request: ValidateRequest) -> ValidationPlan:
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

        cached_intent = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="intent_summary",
        )
        if cached_intent:
            intent = IntentSummary(
                intent_score=float(cached_intent.get("intent_score", 0.5)),
                intent_label=str(cached_intent.get("intent_label", "uncertain")),
                signals=list(cached_intent.get("signals", [])),
            )
        else:
            intent = classify_intent(
                change_summary,
                repo_path=str(self._repo),
                feature_ref=self._resolved_feature,
            )
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="intent_summary",
                    value={
                        "intent_score": intent.intent_score,
                        "intent_label": intent.intent_label,
                        "signals": intent.signals,
                    },
                )

        cached_conf = None if request.nocache else read_cache(
            repo_id=repo_id,
            base_sha=base_sha,
            feature_sha=feature_sha,
            key="confidence_summary",
        )
        if cached_conf:
            confidence = ConfidenceSummary(
                score=float(cached_conf.get("score", 0.5)),
                level=str(cached_conf.get("level", "Medium")),
                reasons=list(cached_conf.get("reasons", [])),
            )
        else:
            confidence = compute_confidence(change_summary, intent)
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="confidence_summary",
                    value={
                        "score": confidence.score,
                        "level": confidence.level,
                        "reasons": confidence.reasons,
                    },
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
            plan = ValidationPlan(raw_output=str(cached_plan.get("raw_output", "")).strip())
        else:
            plan = generate_validation_plan(
                change_summary,
                impact,
                risk,
                intent_summary=intent,
                confidence_summary=confidence,
                config=dict(self.config),
            )
            if not request.nocache:
                write_cache(
                    repo_id=repo_id,
                    base_sha=base_sha,
                    feature_sha=feature_sha,
                    key="validation_plan",
                    value={"raw_output": plan.raw_output},
                )

        def strip_leading_section(text: str, header: str) -> str:
            s = (text or "").lstrip()
            if not s.startswith(header):
                return text
            # Drop until the first blank line after header block.
            parts = s.split("\n\n", 1)
            return parts[1] if len(parts) == 2 else ""

        # Ensure intent + confidence are printed first (deterministic).
        intent_conf = "High" if intent.intent_score >= 0.75 else ("Medium" if intent.intent_score >= 0.5 else "Low")
        intent_label = intent.intent_label.capitalize()
        intent_header = f"🧭 Change Intent:\n{intent_label} ({intent_conf} Confidence)\n\n"

        conf_lines = "\n".join(f"- {r}" for r in (confidence.reasons or [])[:5])
        conf_header = f"🎯 Analysis Confidence:\n{confidence.level}\n{conf_lines}\n\n"

        body = plan.raw_output
        body = strip_leading_section(body, "🧭 Change Intent:")
        body = strip_leading_section(body, "🎯 Analysis Confidence:")

        def adjust_merge_risk(risk: str, confidence_summary: ConfidenceSummary) -> str:
            if confidence_summary.level == "Low":
                if risk == "HIGH":
                    return "MEDIUM"
                if risk == "MEDIUM":
                    return "LOW"
            return risk

        def calibrate_merge_risk(text: str) -> str:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if line.strip().lower().startswith("🚨 merge risk"):
                    # value is typically on next non-empty line
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines):
                        val = lines[j].strip().upper()
                        new_val = adjust_merge_risk(val, confidence)
                        if new_val != val:
                            lines[j] = new_val
                    break
            return "\n".join(lines)

        body = calibrate_merge_risk(body.lstrip())
        plan = ValidationPlan(raw_output=intent_header + conf_header + body)

        return plan
