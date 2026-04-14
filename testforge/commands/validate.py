"""testforge validate — change-aware validation assistant."""

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
    run: bool = typer.Option(
        False,
        "--run",
        help="Actively execute lightweight validations (v1 simulated mode).",
    ),
    nocache: bool = typer.Option(
        False,
        "--nocache",
        help="Bypass the local cache and run the full pipeline.",
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
        run=run,
        nocache=nocache,
    )
    result = ValidationService(app_ctx).run(request)

    typer.echo("🔍 Analyzing changes...\n")

    if hasattr(result, "scenarios"):
        plan = result  # ValidationPlan

        cs = getattr(plan, "_change_summary", None)
        impact = getattr(plan, "_impact_summary", None)
        risk = getattr(plan, "_risk_summary", None)

        typer.echo("📦 Changed:")
        if cs and getattr(cs, "functions", None):
            for fn in cs.functions:
                typer.echo(f"- {fn}()")
        elif cs and getattr(cs, "files", None):
            for fp in cs.files[:10]:
                typer.echo(f"- {fp}")
        else:
            typer.echo("- (no changes detected)")

        typer.echo("\n🌐 Impact:")
        if impact and getattr(impact, "endpoints", None):
            for ep in impact.endpoints:
                typer.echo(f"- {ep}")
        else:
            typer.echo("- (no endpoints mapped)")

        typer.echo("\n⚠️ Risk:")
        if risk and getattr(risk, "types", None):
            for t in risk.types:
                typer.echo(f"- {t}")
        else:
            typer.echo("- unknown")

        typer.echo("\n🧠 Suggested validation:")
        for i, s in enumerate(plan.scenarios, 1):
            typer.echo(f"{i}. {s}")
        return

    report = result
    for line in report._display_lines():  # type: ignore[attr-defined]
        typer.echo(line)
