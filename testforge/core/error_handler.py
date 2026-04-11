"""Centralized CLI error handling."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

import typer

from testforge.core.exceptions import ConfigError, TestForgeError, ValidationError
from testforge.core.exit_codes import ExitCodes

F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(fn: F) -> F:
    """
    Wrap a Typer command: map exceptions to stderr messages and process exit codes.

    ``typer.Exit`` and ``SystemExit`` are re-raised unchanged.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except (typer.Exit, SystemExit, KeyboardInterrupt):
            raise
        except ValidationError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(ExitCodes.VALIDATION_ERROR)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(ExitCodes.CONFIG_ERROR)
        except TestForgeError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(ExitCodes.UNKNOWN_ERROR)
        except Exception:
            typer.secho(
                "An unexpected error occurred. Use --verbose for details.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(ExitCodes.UNKNOWN_ERROR)

    return wrapper  # type: ignore[return-value]
