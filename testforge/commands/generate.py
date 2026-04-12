"""testforge generate — stub for test generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from testforge.core.context import require_app_context
from testforge.core.error_handler import handle_errors
from testforge.core.models.requests import GenerateRequest
from testforge.core.services import TestGenerationService

generate_app = typer.Typer(
    help="Generate tests for a Python service.",
    epilog="Example:\n  testforge generate --path ./services/api",
    invoke_without_command=True,
)


@generate_app.callback()
@handle_errors
def generate(
    ctx: typer.Context,
    path: str = typer.Option(
        ...,
        "--path",
        help="Path to the Python service or package.",
        show_default=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Directory to write generated tests (optional).",
        file_okay=False,
        dir_okay=True,
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Optional path to a TestForge config file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """Generate tests for a Python tree (delegates to :class:`TestGenerationService`)."""
    app_ctx = require_app_context(ctx)
    request = GenerateRequest(
        path=path,
        output=str(output) if output else None,
        config_path=str(config) if config else None,
    )
    TestGenerationService(app_ctx).run(request)
