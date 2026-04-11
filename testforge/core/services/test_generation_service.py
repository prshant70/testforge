"""Test generation orchestration (stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from testforge.core.context import AppContext


class TestGenerationService:
    """Coordinates scanning a service and emitting tests."""

    def run(
        self,
        *,
        path: Path,
        output: Optional[Path],
        config_path: Optional[Path],
        app_ctx: AppContext,
    ) -> str:
        """
        Entry point for ``testforge generate``.

        Returns a human-readable status line for the CLI to print.
        """
        _ = app_ctx
        _ = config_path
        # TODO: Merge app_ctx.config with optional on-disk config override.
        # TODO: Discover Python modules, build prompts or templates, write test files under `output`.
        out_msg = f", output → {output}" if output else ""
        cfg_msg = f", config → {config_path}" if config_path else ""
        return f"Generating tests for {path}{out_msg}{cfg_msg}"
