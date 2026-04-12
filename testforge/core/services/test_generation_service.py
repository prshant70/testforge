"""Test generation orchestration (stub)."""

from __future__ import annotations

from pathlib import Path

from testforge.core.context import AppContext
from testforge.core.models.requests import GenerateRequest
from testforge.core.validator import validate_path_exists


class TestGenerationService:
    """Coordinates scanning a service and emitting tests."""

    def __init__(self, ctx: AppContext) -> None:
        self.config = ctx.config
        self.logger = ctx.logger

    def run(self, request: GenerateRequest) -> None:
        self._validate(request)
        self._execute(request)

    def _validate(self, request: GenerateRequest) -> None:
        validate_path_exists(request.path, kind="Service path")
        if request.config_path:
            validate_path_exists(request.config_path, kind="Config file")

    def _execute(self, request: GenerateRequest) -> None:
        # TODO: Merge self.config with optional on-disk config override.
        # TODO: Discover Python modules, build prompts or templates, write test files.
        out_msg = ""
        if request.output:
            out_msg = f", output → {request.output}"
        cfg_msg = ""
        if request.config_path:
            cfg_msg = f", config → {request.config_path}"
        resolved = Path(request.path).expanduser().resolve()
        self.logger.info(
            "Generating tests for %s%s%s",
            resolved,
            out_msg,
            cfg_msg,
        )
