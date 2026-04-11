"""Domain exceptions for TestForge."""


class TestForgeError(Exception):
    """Base error for all TestForge failures."""


class ValidationError(TestForgeError):
    """Raised when user input or environment fails validation."""


class PathValidationError(ValidationError):
    """Raised when a filesystem path is missing or invalid."""


class BranchValidationError(ValidationError):
    """Raised when a Git branch or ref cannot be resolved."""


class ConfigError(TestForgeError):
    """Raised for configuration load/save problems."""


class ConfigNotFoundError(ConfigError):
    """Raised when a required config file is missing."""
