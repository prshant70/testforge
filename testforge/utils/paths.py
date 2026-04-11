"""Filesystem paths used by TestForge."""

from pathlib import Path


def get_config_dir() -> Path:
    """Return the user config directory (~/.testforge)."""
    return Path.home() / ".testforge"


def get_config_file() -> Path:
    """Return the default config file path."""
    return get_config_dir() / "config.yaml"
