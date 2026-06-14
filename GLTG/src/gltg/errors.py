"""GLTG exception hierarchy."""


class GLTGError(Exception):
    """Base exception for all GLTG errors."""


class InfeasibleOrderError(GLTGError):
    """Raised when an order cannot be processed due to hard constraints."""


class MissingRequiredFieldError(GLTGError):
    """Raised when a required field is absent from the input."""

    def __init__(self, field_name: str, message: str | None = None):
        self.field_name = field_name
        super().__init__(message or f"Required field missing: {field_name}")


class GraphResolutionError(GLTGError):
    """Raised when the lead-time graph cannot be resolved to valid dates."""


class CyclicDependencyError(GraphResolutionError):
    """Raised when a cycle is detected in the dependency graph."""

    def __init__(self, cycle: list[str] | None = None):
        self.cycle = cycle or []
        cycle_str = " -> ".join(self.cycle) if self.cycle else "unknown"
        super().__init__(f"Cyclic dependency detected: {cycle_str}")
