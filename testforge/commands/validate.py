"""testforge validate — stub for regression validation between branches."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from testforge.core.context import require_app_context
from testforge.core.error_handler import handle_errors
from testforge.core.services import ValidationService
from testforge.core.validator import validate_git_branch, validate_path_exists

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
    """Check for behavioral regressions between branches (stub)."""
    app_ctx = require_app_context(ctx)
    repo = validate_path_exists(path, kind="Repository path") if path else None
    b = validate_git_branch(base, repo=repo)
    f = validate_git_branch(feature, repo=repo)
    msg = ValidationService().run(base=b, feature=f, repo=repo, app_ctx=app_ctx)
    typer.echo(msg)
