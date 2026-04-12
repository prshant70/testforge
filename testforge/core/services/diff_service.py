"""Branch diff analysis (stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext
from testforge.core.models.requests import DiffRequest
from testforge.core.validator import validate_git_branch, validate_path_exists


class DiffService:
    """Compares two refs and summarizes changes."""

    def __init__(self, ctx: AppContext) -> None:
        self.config = ctx.config
        self.logger = ctx.logger

    def run(self, request: DiffRequest) -> None:
        self._validate(request)
        self._execute(request)

    def _validate(self, request: DiffRequest) -> None:
        repo: Optional[Path] = None
        if request.path:
            repo = validate_path_exists(request.path, kind="Repository path")
        base = validate_git_branch(request.base, repo=repo)
        feature = validate_git_branch(request.feature, repo=repo)
        self._resolved_base = base
        self._resolved_feature = feature

    def _execute(self, request: DiffRequest) -> None:
        # TODO: Collect `git diff` / name-status, optional AST or import graph summary.
        _ = request
        self.logger.info(
            "Analyzing diff between %s and %s",
            self._resolved_base,
            self._resolved_feature,
        )
