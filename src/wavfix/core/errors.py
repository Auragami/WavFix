"""Core error types for processing workflows."""


class WavFixCoreError(Exception):
    """Base class for core processing errors."""


class OutputPlanningError(WavFixCoreError):
    """Raised when output path planning cannot be completed."""
