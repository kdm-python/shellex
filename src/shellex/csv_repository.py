"""File-backed repository; CSV and notes remain editable outside Shellex."""

import csv
import io
import os
import tempfile
from pathlib import Path

from .errors import ShellexError
from .models import Example


class CsvRepository:
    def __init__(self, root: Path):
        self.root = root.expanduser()

    def _group(self, name: str) -> Path:
        path = self.root / name
        if not path.is_dir() or path.is_symlink():
            raise ShellexError(f"Group {name!r} does not exist.")
        return path

    def list_names(self) -> list[str]:
        if not self.root.exists():
            return []
        if not self.root.is_dir():
            raise ShellexError(f"Data path is not a directory: {self.root}")
        return sorted(
            p.name for p in self.root.iterdir() if p.is_dir() and not p.is_symlink()
        )

    def create_group(self, name: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        group = self.root / name
        try:
            group.mkdir()
        except FileExistsError:
            raise ShellexError(f"Group {name!r} already exists.")
        try:
            (group / (name + ".csv")).write_text(
                "command,description\n", encoding="utf-8"
            )
            (group / (name + ".md")).write_text("", encoding="utf-8")
        except OSError:
            # Only remove files and the directory created by this operation.
            for suffix in (".csv", ".md"):
                try:
                    (group / (name + suffix)).unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                group.rmdir()
            except OSError:
                pass
            raise

    def read_examples(self, name: str) -> tuple[list[Example], bytes]:
        path = self._group(name) / (name + ".csv")
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            raise ShellexError(f"Examples file is missing: {path}")
        if not raw:
            return [], raw
        try:
            reader = csv.reader(
                io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True
            )
            rows = list(reader)
        except (UnicodeDecodeError, csv.Error) as exc:
            raise ShellexError(f"Cannot read CSV {path}: {exc}")
        if not rows or rows[0] != ["command", "description"]:
            raise ShellexError(
                f"Invalid CSV header in {path}: expected command,description."
            )
        examples = []
        for row_number, row in enumerate(rows[1:], 2):
            if len(row) != 2 or not row[0].strip():
                raise ShellexError(
                    f"Invalid CSV record {row_number} in {path}: expected a non-empty command and a description."
                )
            examples.append(Example(*row))
        return examples, raw

    def write_examples(
        self, name: str, examples: list[Example], original: bytes
    ) -> None:
        path = self._group(name) / (name + ".csv")
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["command", "description"])
        writer.writerows((e.command, e.description) for e in examples)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=path.parent,
                prefix=".shellex-",
                delete=False,
            ) as handle:
                tmp = Path(handle.name)
                handle.write(output.getvalue())
                handle.flush()
                os.fsync(handle.fileno())
            # Preserve file permissions when replacing a manually edited file.
            os.chmod(tmp, path.stat().st_mode & 0o777)
            if path.read_bytes() != original:
                raise ShellexError("Examples changed on disk; reload and try again.")
            os.replace(str(tmp), str(path))
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink()

    def notes_path(self, name: str) -> Path:
        group = self._group(name)
        markdown = group / (name + ".md")
        legacy = group / (name + ".txt")
        if markdown.exists():
            return markdown
        if legacy.exists():
            return legacy
        raise ShellexError(f"Notes file is missing for group {name!r}.")

    def read_notes(self, name: str) -> str:
        path = self.notes_path(name)
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ShellexError(f"Cannot read notes {path}: {exc}")
