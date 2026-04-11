"""Performance comparison (stub)."""

from __future__ import annotations

from testforge.core.context import AppContext


class PerfService:
    """Placeholder for future benchmark workflows."""

    def run(self, *, app_ctx: AppContext) -> str:
        """Entry point for ``testforge perf``."""
        _ = app_ctx
        # TODO: Record baselines, run workloads, compare across branches or commits.
        return "Performance analysis not implemented yet"
