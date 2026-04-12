"""testforge diff — stub for branch diff analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from testforge.core.context import require_app_context
from testforge.core.error_handler import handle_errors
from testforge.core.models.requests import DiffRequest
from testforge.core.services import DiffService

diff_app = typer.Typer(
    help="Analyze code differences between two branches.",
    epilog="Example:\n  testforge diff --base main --feature feature/oauth",
    invoke_without_command=True,
)


@diff_app.callback()
@handle_errors
def diff(
    ctx: typer.Context,
    base: str = typer.Option(
        ...,
        "--base",
        help="Base branch or ref to compare from.",
    ),
    feature: str = typer.Option(
        ...,
        "--feature",
        help="Feature branch or ref to compare against the base.",
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
    """Compare two refs (delegates to :class:`DiffService`)."""
    app_ctx = require_app_context(ctx)
    request = DiffRequest(
        base=base,
        feature=feature,
        path=str(path) if path else None,
    )
    DiffService(app_ctx).run(request)
