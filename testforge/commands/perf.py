"""testforge perf — placeholder for future performance comparison."""

import typer

from testforge.core.context import require_app_context
from testforge.core.error_handler import handle_errors
from testforge.core.services import PerfService

perf_app = typer.Typer(
    help="Compare performance across branches or builds (coming soon).",
    invoke_without_command=True,
)


@perf_app.callback()
@handle_errors
def perf(ctx: typer.Context) -> None:
    """Placeholder command; no analysis is run yet."""
    app_ctx = require_app_context(ctx)
    typer.echo(PerfService().run(app_ctx=app_ctx))
