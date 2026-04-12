"""Performance comparison (stub)."""

from __future__ import annotations

from testforge.core.context import AppContext
from testforge.core.models.requests import PerfRequest


class PerfService:
    """Placeholder for future benchmark workflows."""

    def __init__(self, ctx: AppContext) -> None:
        self.config = ctx.config
        self.logger = ctx.logger

    def run(self, request: PerfRequest) -> None:
        self._validate(request)
        self._execute(request)

    def _validate(self, request: PerfRequest) -> None:
        _ = request

    def _execute(self, request: PerfRequest) -> None:
        _ = request
        # TODO: Record baselines, run workloads, compare across branches or commits.
        self.logger.info("Performance analysis not implemented yet")
