"""Branch diff analysis (stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext


class DiffService:
    """Compares two refs and summarizes changes."""

    def run(
        self,
        *,
        base: str,
        feature: str,
        repo: Optional[Path],
        app_ctx: AppContext,
    ) -> str:
        """Entry point for ``testforge diff``."""
        _ = app_ctx
        _ = repo
        # TODO: Collect `git diff` / name-status, optional AST or import graph summary.
        return f"Analyzing diff between {base} and {feature}"
