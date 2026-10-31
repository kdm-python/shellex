"""Data shared by the application service and its clients."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    """A command and its optional human-readable description."""

    command: str
    description: str = ""


@dataclass(frozen=True)
class Group:
    """A group name and the number of examples it currently contains."""

    name: str
    example_count: int
