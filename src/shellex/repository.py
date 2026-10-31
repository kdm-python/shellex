"""Storage contract for the application service."""

from pathlib import Path
from typing import Protocol

from .models import Example


class Repository(Protocol):
    """Storage operations required by the service, including change tokens.

    read_examples returns the original file bytes; write_examples uses them
    to detect changes made between reading and writing.
    """

    def list_names(self) -> list[str]: ...
    def create_group(self, name: str) -> None: ...
    def read_examples(self, name: str) -> tuple[list[Example], bytes]: ...
    def write_examples(
        self, name: str, examples: list[Example], original: bytes
    ) -> None: ...
    def notes_path(self, name: str) -> Path: ...
    def read_notes(self, name: str) -> str: ...
