"""Command-line interface for Shellex."""

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

from .csv_repository import CsvRepository
from .errors import ShellexError
from .presentation import Presentation
from .service import ShellexService


def parser():
    """Build the CLI grammar, including the current environment defaults."""
    p = argparse.ArgumentParser(
        prog="shellex", description="Organise shell command examples and notes."
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("SHELLEX_DIR") or "~/.shellex"),
        help="data directory (default: SHELLEX_DIR or ~/.shellex)",
    )
    commands = p.add_subparsers(dest="action", required=True)
    commands.add_parser("list", help="list groups")
    new = commands.add_parser("new", help="create a group")
    new.add_argument("group")
    examples = commands.add_parser("examples", help="show numbered examples")
    examples.add_argument("group")
    add = commands.add_parser("add", help="add an example")
    add.add_argument("group")
    add.add_argument(
        "--command", required=True, help="command text; quote it for your shell"
    )
    add.add_argument("--description", default="")
    update = commands.add_parser(
        "update", help="update an example by its current row number"
    )
    update.add_argument("group")
    update.add_argument("row", type=int)
    update.add_argument("--command")
    update.add_argument(
        "--description", help="use an empty string to clear the description"
    )
    delete = commands.add_parser(
        "delete", help="delete an example by its current row number"
    )
    delete.add_argument("group")
    delete.add_argument("row", type=int)
    delete.add_argument(
        "--yes", "-y", action="store_true", help="delete without confirmation"
    )
    notes = commands.add_parser("notes", help="show or edit notes")
    notes.add_argument("group")
    notes.add_argument(
        "--edit", action="store_true", help="open notes in VISUAL or EDITOR"
    )
    return p


def edit_notes(path):
    """Open a notes file with the configured editor and wait for it to exit."""
    value = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    # Split editor arguments without invoking a shell or interpreting the path.
    try:
        editor = shlex.split(value)
    except ValueError as exc:
        raise ShellexError(f"Invalid editor setting: {exc}")
    if not editor:
        raise ShellexError("Editor setting is empty.")
    try:
        result = subprocess.run(editor + [str(path)], check=False)
    except OSError as exc:
        raise ShellexError(f"Could not start editor: {exc}")
    if result.returncode:
        raise ShellexError(f"Editor exited with status {result.returncode}.")


def main(argv=None):
    """Load configuration, dispatch a CLI operation, and return its exit status."""
    # Existing environment variables take precedence over values in .env.
    load_dotenv()
    args = parser().parse_args(argv)
    view = Presentation()
    service = ShellexService(CsvRepository(args.data_dir))
    try:
        if args.action == "list":
            view.groups(service.list_groups())
        elif args.action == "new":
            service.create_group(args.group)
            view.console.print(f"Created group {args.group}.", style="green")
        elif args.action == "examples":
            view.examples(service.examples(args.group))
        elif args.action == "add":
            service.add(args.group, args.command, args.description)
            view.console.print("Example added.", style="green")
        elif args.action == "update":
            service.update(args.group, args.row, args.command, args.description)
            view.console.print("Example updated.", style="green")
        elif args.action == "delete":
            selected = service.select(args.group, args.row)
            if not args.yes:
                view.examples([selected], start=args.row)
                if not sys.stdin.isatty():
                    raise ShellexError(
                        "Confirmation requires a terminal; use --yes to delete non-interactively."
                    )
                if input("Delete this example? [y/N] ").strip().lower() not in (
                    "y",
                    "yes",
                ):
                    view.console.print("Deletion cancelled.")
                    return 0
            service.delete(args.group, args.row, selected)
            view.console.print("Example deleted.", style="green")
        elif args.action == "notes":
            if args.edit:
                edit_notes(service.notes_path(args.group))
            else:
                content = service.notes(args.group)
                view.notes(content, service.notes_path(args.group).suffix == ".md")
        return 0
    except (ShellexError, OSError) as exc:
        view.error.print(f"Error: {exc}", style="bold red")
        return 1
