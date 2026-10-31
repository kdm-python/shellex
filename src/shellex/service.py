"""Application operations, independent of the command-line interface."""

from __future__ import annotations

import re

from .errors import ShellexError
from .models import Example, Group
from .repository import Repository


class ShellexService:
    """Apply application rules independently of storage and presentation."""

    def __init__(self, repository: Repository):
        """Use the supplied repository for all group data."""
        self.repository = repository

    @staticmethod
    def validate_name(name: str) -> None:
        """Reject names that are unsafe as portable single directory names."""
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", name) or name.endswith("."):
            raise ShellexError(
                f"Invalid group name {name!r}. Use letters, numbers, underscores, hyphens or dots; start with a letter, number or underscore."
            )
        if name.split(".")[0].upper() in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }:
            raise ShellexError(f"Invalid group name {name!r}: reserved device name.")

    @staticmethod
    def validate_command(command: str) -> None:
        """Require command text with at least one non-whitespace character."""
        if not command.strip():
            raise ShellexError("Command must not be empty.")

    def list_groups(self) -> list[Group]:
        """Return groups with counts computed from their current examples."""
        groups = []
        for name in self.repository.list_names():
            self.validate_name(name)
            examples, _ = self.repository.read_examples(name)
            groups.append(Group(name, len(examples)))
        return groups

    def create_group(self, name: str) -> None:
        """Validate and create an empty group."""
        self.validate_name(name)
        self.repository.create_group(name)

    def examples(self, name: str) -> list[Example]:
        """Return the current ordered examples for a group."""
        self.validate_name(name)
        return self.repository.read_examples(name)[0]

    @staticmethod
    def _index(row: int, examples: list[Example]) -> int:
        """Convert a user-facing row number into a validated list index."""
        if row < 1 or row > len(examples):
            raise ShellexError(
                f"Row {row} does not exist; list the examples to see current row numbers."
            )
        return row - 1

    def add(self, name: str, command: str, description: str = "") -> None:
        """Append an example without overwriting a detected external edit."""
        self.validate_name(name)
        self.validate_command(command)
        examples, original = self.repository.read_examples(name)
        examples.append(Example(command, description))
        self.repository.write_examples(name, examples, original)

    def update(
        self,
        name: str,
        row: int,
        command: str | None = None,
        description: str | None = None,
    ) -> None:
        """Update supplied fields; None leaves a field unchanged."""
        self.validate_name(name)
        if command is None and description is None:
            raise ShellexError("Specify --command, --description, or both.")
        if command is not None:
            self.validate_command(command)
        examples, original = self.repository.read_examples(name)
        index = self._index(row, examples)
        old = examples[index]
        examples[index] = Example(
            old.command if command is None else command,
            old.description if description is None else description,
        )
        self.repository.write_examples(name, examples, original)

    def select(self, name: str, row: int) -> Example:
        """Return the example currently displayed at a one-based row."""
        examples = self.examples(name)
        return examples[self._index(row, examples)]

    def delete(self, name: str, row: int, expected: Example) -> None:
        """Delete a row only if it still matches the example selected earlier."""
        self.validate_name(name)
        examples, original = self.repository.read_examples(name)
        index = self._index(row, examples)
        if examples[index] != expected:
            raise ShellexError(
                "Selected example changed; list the examples and try again."
            )
        del examples[index]
        self.repository.write_examples(name, examples, original)

    def notes(self, name: str) -> str:
        """Return a group’s notes as text."""
        self.validate_name(name)
        return self.repository.read_notes(name)

    def notes_path(self, name: str):
        """Return the notes path for opening in an editor."""
        self.validate_name(name)
        return self.repository.notes_path(name)
