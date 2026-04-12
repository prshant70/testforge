"""CLI-facing request payloads passed into services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GenerateRequest:
    path: str
    output: Optional[str] = None
    config_path: Optional[str] = None


@dataclass
class DiffRequest:
    base: str
    feature: str
    path: Optional[str] = None


@dataclass
class ValidateRequest:
    base: str
    feature: str
    path: Optional[str] = None


@dataclass
class PerfRequest:
    """Placeholder request for ``testforge perf`` (no parameters yet)."""

    pass
