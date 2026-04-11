"""Regression validation between branches (stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext


class ValidationService:
    """Runs checks to catch regressions between two refs."""

    def run(
        self,
        *,
        base: str,
        feature: str,
        repo: Optional[Path],
        app_ctx: AppContext,
    ) -> str:
        """Entry point for ``testforge validate``."""
        _ = app_ctx
        _ = repo
        # TODO: Map diff to tests, run pytest with policies, aggregate results.
        return f"Validating regressions between {base} and {feature}"
