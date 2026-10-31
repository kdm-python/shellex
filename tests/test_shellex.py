import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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
        self.service.create_group('journalctl')

    def test_crud_and_csv_round_trip(self):
        command = 'echo "hello, 世界" | grep \'hello\'\nprintf done'
        self.service.add('journalctl', command, 'A, "description"')
        self.service.add('journalctl', 'sudo true')
        self.assertEqual(self.service.examples('journalctl')[0], Example(command, 'A, "description"'))
        self.service.update('journalctl', 1, description='')
        self.assertEqual(self.service.examples('journalctl')[0], Example(command, ''))
        self.service.delete('journalctl', 1, Example(command, ''))
        self.assertEqual(self.service.examples('journalctl'), [Example('sudo true')])
        self.assertEqual(self.service.list_groups()[0].example_count, 1)

    def test_empty_legacy_files_and_notes(self):
        folder = self.root / 'legacy'
        folder.mkdir()
        (folder / 'legacy.csv').write_bytes(b'')
        (folder / 'legacy.txt').write_text('legacy notes', encoding='utf-8')
        self.assertEqual(self.service.examples('legacy'), [])
        self.assertEqual(self.service.notes('legacy'), 'legacy notes')
        self.service.add('legacy', 'echo ok')
        self.assertEqual(self.service.examples('legacy'), [Example('echo ok')])

    def test_bad_inputs_and_duplicate(self):
        for name in ('../oops', '.', 'bad/name', 'bad name', 'CON'):
            with self.subTest(name=name), self.assertRaises(ShellexError):
                self.service.create_group(name)
        with self.assertRaises(ShellexError):
            self.service.create_group('journalctl')
        with self.assertRaises(ShellexError):
            self.service.add('journalctl', '  ')
        with self.assertRaises(ShellexError):
            self.service.update('journalctl', 1)
        with self.assertRaises(ShellexError):
            self.service.select('journalctl', 0)

    def test_malformed_csv_is_not_overwritten(self):
        path = self.root / 'journalctl' / 'journalctl.csv'
        for bad in ('wrong,header\na,b\n', 'command,description\n"unterminated', 'command,description\na,b,c\n'):
            path.write_text(bad, encoding='utf-8')
            with self.assertRaises(ShellexError):
                self.service.add('journalctl', 'echo hi')
            self.assertEqual(path.read_text(encoding='utf-8'), bad)

    def test_detects_external_edit(self):
        examples, original = self.repo.read_examples('journalctl')
        path = self.root / 'journalctl' / 'journalctl.csv'
        path.write_text('command,description\nother,\n', encoding='utf-8')
        with self.assertRaisesRegex(ShellexError, 'changed on disk'):
            self.repo.write_examples('journalctl', examples, original)
        self.assertIn('other', path.read_text())

    def test_selected_example_must_still_match(self):
        self.service.add('journalctl', 'one')
        selected = self.service.select('journalctl', 1)
        self.service.update('journalctl', 1, command='two')
        with self.assertRaises(ShellexError):
            self.service.delete('journalctl', 1, selected)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'), NO_COLOR='1')

    def run_cli(self, *args, input_text=None):
        return subprocess.run([sys.executable, '-m', 'shellex', '--data-dir', str(self.root), *args], env=self.env, input=input_text, text=True, capture_output=True)

    def test_full_cli(self):
        self.assertEqual(self.run_cli('new', 'sudo').returncode, 0)
        self.assertTrue((self.root / 'sudo' / 'sudo.md').exists())
        self.assertEqual(self.run_cli('add', 'sudo', '--command', 'echo a | grep a', '--description', 'test').returncode, 0)
        self.assertIn('echo a | grep a', self.run_cli('examples', 'sudo').stdout)
        self.assertEqual(self.run_cli('update', 'sudo', '1', '--description', '').returncode, 0)
        self.assertNotEqual(self.run_cli('delete', 'sudo', '1', input_text='y\n').returncode, 0)
        self.assertEqual(self.run_cli('delete', 'sudo', '1', '--yes').returncode, 0)
        self.assertIn('sudo', self.run_cli('list').stdout)

    def test_raw_markdown_and_editor(self):
        self.run_cli('new', 'sudo')
        path = self.root / 'sudo' / 'sudo.md'
        path.write_text('# Heading\n\n**bold**\n', encoding='utf-8')
        self.assertEqual(self.run_cli('notes', 'sudo').stdout, path.read_text())
        self.env['VISUAL'] = '/nonexistent/editor'
        result = self.run_cli('notes', 'sudo', '--edit')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Could not start editor', result.stderr)


if __name__ == '__main__':
    unittest.main()
