"""testforge validate — stub for regression validation between branches."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from testforge.core.context import require_app_context
from testforge.core.error_handler import handle_errors
from testforge.core.models.requests import ValidateRequest
from testforge.core.services import ValidationService

validate_app = typer.Typer(
    help="Validate regressions between two branches.",
    epilog="Example:\n  testforge validate --base main --feature feature/payments",
    invoke_without_command=True,
)


@validate_app.callback()
@handle_errors
def validate(
    ctx: typer.Context,
    base: str = typer.Option(
        ...,
        "--base",
        help="Base branch or ref.",
    ),
    feature: str = typer.Option(
        ...,
        "--feature",
        help="Feature branch or ref to validate against the base.",
    ),
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Git repository root (defaults to current directory).",
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Check for regressions between branches (delegates to :class:`ValidationService`)."""
    app_ctx = require_app_context(ctx)
    request = ValidateRequest(
        base=base,
        feature=feature,
        path=str(path) if path else None,
    )
    ValidationService(app_ctx).run(request)
