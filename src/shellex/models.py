"""Data shared by the application service and its clients."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    command: str
    description: str = ""


@dataclass(frozen=True)
class Group:
    name: str
    example_count: int
