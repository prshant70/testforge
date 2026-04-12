"""Regression validation between branches (stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext
from testforge.core.models.requests import ValidateRequest
from testforge.core.validator import validate_git_branch, validate_path_exists


class ValidationService:
    """Runs checks to catch regressions between two refs."""

    def __init__(self, ctx: AppContext) -> None:
        self.config = ctx.config
        self.logger = ctx.logger

    def run(self, request: ValidateRequest) -> None:
        self._validate(request)
        self._execute(request)

    def _validate(self, request: ValidateRequest) -> None:
        repo: Optional[Path] = None
        if request.path:
            repo = validate_path_exists(request.path, kind="Repository path")
        base = validate_git_branch(request.base, repo=repo)
        feature = validate_git_branch(request.feature, repo=repo)
        self._resolved_base = base
        self._resolved_feature = feature

    def _execute(self, request: ValidateRequest) -> None:
        _ = request
        # TODO: Map diff to tests, run pytest with policies, aggregate results.
        self.logger.info(
            "Validating regressions between %s and %s",
            self._resolved_base,
            self._resolved_feature,
        )
