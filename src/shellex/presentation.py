"""Human-readable terminal output."""

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text


class Presentation:
    """Render CLI results and errors using terminal-aware Rich consoles."""

    def __init__(self):
        """Create separate consoles for normal output and errors."""
        self.console = Console(highlight=False)
        self.error = Console(stderr=True, highlight=False)

    def groups(self, groups):
        """Display the available groups and their example counts."""
        if not groups:
            self.console.print("No groups found. Create one with shellex new GROUP.")
            return
        table = Table("Group", "Examples", header_style="bold cyan")
        for group in groups:
            table.add_row(group.name, str(group.example_count))
        self.console.print(table)

    def examples(self, examples, start=1):
        """Display examples with their current one-based row numbers."""
        if not examples:
            self.console.print("No examples yet.")
            return
        table = Table("#", "Command", "Description", header_style="bold cyan")
        for number, example in enumerate(examples, start):
            table.add_row(str(number), Text(example.command), Text(example.description))
        self.console.print(table)

    def notes(self, content, markdown):
        """Render Markdown on a terminal and preserve raw redirected output."""
        if not content:
            self.console.print("No notes yet.")
        elif self.console.is_terminal and markdown:
            self.console.print(Markdown(content))
        else:
            # Preserve redirected output exactly.
            sys.stdout.write(content)
