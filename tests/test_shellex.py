import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shellex.clipboard import copy_text
from shellex.cli import main
from shellex.csv_repository import CsvRepository
from shellex.errors import ShellexError
from shellex.models import Example
from shellex.service import ShellexService


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = CsvRepository(self.root)
        self.service = ShellexService(self.repo)
        self.service.create_group("journalctl")

    def test_crud_and_csv_round_trip(self):
        command = "echo \"hello, 世界\" | grep 'hello'\nprintf done"
        self.service.add("journalctl", command, 'A, "description"')
        self.service.add("journalctl", "sudo true")
        self.assertEqual(
            self.service.examples("journalctl")[0], Example(command, 'A, "description"')
        )
        self.service.update("journalctl", 1, description="")
        self.assertEqual(self.service.examples("journalctl")[0], Example(command, ""))
        self.service.delete("journalctl", 1, Example(command, ""))
        self.assertEqual(self.service.examples("journalctl"), [Example("sudo true")])
        self.assertEqual(self.service.list_groups()[0].example_count, 1)

    def test_empty_legacy_files_and_notes(self):
        folder = self.root / "legacy"
        folder.mkdir()
        (folder / "legacy.csv").write_bytes(b"")
        (folder / "legacy.txt").write_text("legacy notes", encoding="utf-8")
        self.assertEqual(self.service.examples("legacy"), [])
        self.assertEqual(self.service.notes("legacy"), "legacy notes")
        self.service.add("legacy", "echo ok")
        self.assertEqual(self.service.examples("legacy"), [Example("echo ok")])

    def test_bad_inputs_and_duplicate(self):
        for name in ("../oops", ".", "bad/name", "bad name", "CON"):
            with self.subTest(name=name), self.assertRaises(ShellexError):
                self.service.create_group(name)
        with self.assertRaises(ShellexError):
            self.service.create_group("journalctl")
        with self.assertRaises(ShellexError):
            self.service.add("journalctl", "  ")
        with self.assertRaises(ShellexError):
            self.service.update("journalctl", 1)
        with self.assertRaises(ShellexError):
            self.service.select("journalctl", 0)

    def test_malformed_csv_is_not_overwritten(self):
        path = self.root / "journalctl" / "journalctl.csv"
        for bad in (
            "wrong,header\na,b\n",
            'command,description\n"unterminated',
            "command,description\na,b,c\n",
        ):
            path.write_text(bad, encoding="utf-8")
            with self.assertRaises(ShellexError):
                self.service.add("journalctl", "echo hi")
            self.assertEqual(path.read_text(encoding="utf-8"), bad)

    def test_detects_external_edit(self):
        examples, original = self.repo.read_examples("journalctl")
        path = self.root / "journalctl" / "journalctl.csv"
        path.write_text("command,description\nother,\n", encoding="utf-8")
        with self.assertRaisesRegex(ShellexError, "changed on disk"):
            self.repo.write_examples("journalctl", examples, original)
        self.assertIn("other", path.read_text())

    def test_selected_example_must_still_match(self):
        self.service.add("journalctl", "one")
        selected = self.service.select("journalctl", 1)
        self.service.update("journalctl", 1, command="two")
        with self.assertRaises(ShellexError):
            self.service.delete("journalctl", 1, selected)

    def test_search_fields_and_original_numbers(self):
        self.service.add("journalctl", "echo unrelated", "first")
        self.service.add("journalctl", "journalctl --since today", "View logs")
        self.service.add("journalctl", "VIEW status", "other")
        self.assertEqual([n for n, _ in self.service.search("journalctl", "view")], [2, 3])
        self.assertEqual([n for n, _ in self.service.search("journalctl", "view", "command")], [3])
        self.assertEqual([n for n, _ in self.service.search("journalctl", "VIEW", "description")], [2])
        self.assertEqual(self.service.search("journalctl", "not found"), [])
        with self.assertRaises(ShellexError):
            self.service.search("journalctl", "")


class ClipboardTests(unittest.TestCase):
    @patch("shellex.clipboard.sys.platform", "darwin")
    @patch("shellex.clipboard.shutil.which", return_value="/usr/bin/pbcopy")
    @patch("shellex.clipboard.subprocess.run")
    def test_copies_exact_utf8_text(self, run, which):
        run.return_value.returncode = 0
        copy_text("echo 世界\nnext")
        self.assertEqual(run.call_args.kwargs["input"], "echo 世界\nnext".encode())
        self.assertEqual(run.call_args.args[0], ["/usr/bin/pbcopy"])

    @patch("shellex.clipboard.sys.platform", "darwin")
    @patch("shellex.clipboard.shutil.which", return_value=None)
    def test_missing_clipboard_tool(self, which):
        with self.assertRaisesRegex(ShellexError, "No clipboard tool"):
            copy_text("example")

    @patch("shellex.clipboard.sys.platform", "darwin")
    @patch("shellex.clipboard.shutil.which", return_value="/usr/bin/pbcopy")
    @patch("shellex.clipboard.subprocess.run")
    def test_clipboard_failure(self, run, which):
        run.return_value.returncode = 1
        run.return_value.stderr = b"clipboard unavailable"
        with self.assertRaisesRegex(ShellexError, "clipboard unavailable"):
            copy_text("example")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(
            os.environ,
            PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
            NO_COLOR="1",
        )

    def run_cli(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "shellex", "--data-dir", str(self.root), *args],
            check=False,
            env=self.env,
            input=input_text,
            text=True,
            capture_output=True,
        )

    def test_full_cli(self):
        self.assertEqual(self.run_cli("new", "sudo").returncode, 0)
        self.assertTrue((self.root / "sudo" / "sudo.md").exists())
        self.assertEqual(
            self.run_cli(
                "add", "sudo", "--command", "echo a | grep a", "--description", "test"
            ).returncode,
            0,
        )
        self.assertIn("echo a | grep a", self.run_cli("examples", "sudo").stdout)
        self.assertEqual(
            self.run_cli("update", "sudo", "1", "--description", "").returncode, 0
        )
        self.assertNotEqual(
            self.run_cli("delete", "sudo", "1", input_text="y\n").returncode, 0
        )
        self.assertEqual(self.run_cli("delete", "sudo", "1", "--yes").returncode, 0)
        self.assertIn("sudo", self.run_cli("list").stdout)

    def test_raw_markdown_and_editor(self):
        self.run_cli("new", "sudo")
        path = self.root / "sudo" / "sudo.md"
        path.write_text("# Heading\n\n**bold**\n", encoding="utf-8")
        self.assertEqual(self.run_cli("notes", "sudo").stdout, path.read_text())
        self.env["VISUAL"] = "/nonexistent/editor"
        result = self.run_cli("notes", "sudo", "--edit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not start editor", result.stderr)

    def test_search_cli_shows_original_row(self):
        self.run_cli("new", "sudo")
        self.run_cli("add", "sudo", "--command", "echo other")
        self.run_cli("add", "sudo", "--command", "echo hello", "--description", "View message")
        result = self.run_cli("search", "sudo", "VIEW", "--field", "description")
        self.assertEqual(result.returncode, 0)
        self.assertIn("│ 2", result.stdout)
        self.assertIn("echo hello", result.stdout)
        self.assertNotIn("echo other", result.stdout)
        self.assertIn("No matching examples", self.run_cli("search", "sudo", "missing").stdout)
        self.assertNotEqual(self.run_cli("copy", "sudo", "3").returncode, 0)

    @patch("shellex.cli.copy_text")
    def test_copy_cli_passes_selected_command(self, copy):
        self.run_cli("new", "sudo")
        self.run_cli("add", "sudo", "--command", "first")
        self.run_cli("add", "sudo", "--command", "echo 'second' | cat")
        self.assertEqual(main(["--data-dir", str(self.root), "copy", "sudo", "2"]), 0)
        copy.assert_called_once_with("echo 'second' | cat")


if __name__ == "__main__":
    unittest.main()
