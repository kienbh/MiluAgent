import contextlib
import io
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from milu.memory import MAX_TEXT_LENGTH, MemoryStore, main


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private" / "memory.sqlite3"

    def test_crud_unicode_and_restart(self):
        with MemoryStore(self.path) as store:
            first = store.add("Milu thích chơi 🐶; DROP TABLE memories;")
            record = store.get(first)
            self.assertEqual(record.text, "Milu thích chơi 🐶; DROP TABLE memories;")
            self.assertEqual(record.created_at, record.updated_at)
            self.assertTrue(store.update(first, "Tiếng Việt mới"))
            updated = store.get(first)
            self.assertEqual(updated.created_at, record.created_at)
            self.assertGreaterEqual(updated.updated_at, record.updated_at)
            self.assertEqual(store.list(), [updated])
            self.assertEqual(store._connection.execute("PRAGMA secure_delete").fetchone()[0], 1)
        with MemoryStore(self.path) as store:
            self.assertEqual(store.get(first).text, "Tiếng Việt mới")
            self.assertTrue(store.delete(first))
            self.assertFalse(store.delete(first))
            self.assertIsNone(store.get(first))
            self.assertFalse(store.update(first, "missing"))
            store.add("one")
            store.add("two")
            self.assertEqual(store.clear(), 2)
            self.assertEqual(store.clear(), 0)

    def test_limits_and_rollback(self):
        with MemoryStore(self.path) as store:
            for text in ("", " \n ", "a" * (MAX_TEXT_LENGTH + 1), "a\x00b"):
                with self.assertRaises(ValueError):
                    store.add(text)
            first = store.add("a" * MAX_TEXT_LENGTH)
            with patch("milu.memory.MAX_ENTRIES", 1):
                with self.assertRaises(ValueError):
                    store.add("too many")
            self.assertFalse(store._connection.in_transaction)
            with self.assertRaises(ValueError):
                store.update(first, "")
            store._connection.execute(
                "CREATE TRIGGER fail_update AFTER UPDATE ON memories "
                "BEGIN SELECT RAISE(ABORT, 'simulated failure'); END"
            )
            with self.assertRaises(sqlite3.IntegrityError):
                store.update(first, "must roll back")
            self.assertFalse(store._connection.in_transaction)
            self.assertEqual(store.get(first).text, "a" * MAX_TEXT_LENGTH)
            store._connection.execute("DROP TRIGGER fail_update")
            self.assertTrue(store.update(first, "recovered"))
            self.assertGreater(store.add("still usable"), first)

    def test_private_creation_and_unsafe_paths(self):
        with MemoryStore(self.path):
            pass
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.path.chmod(0o644)
        with self.assertRaises(PermissionError):
            MemoryStore(self.path)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o644)
        self.path.chmod(0o600)
        link = self.path.parent / "link.sqlite3"
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            MemoryStore(link)
        hardlink = self.path.parent / "hard.sqlite3"
        os.link(self.path, hardlink)
        with self.assertRaises(PermissionError):
            MemoryStore(self.path)
        hardlink.unlink()
        sidecar = Path(str(self.path) + "-journal")
        sidecar.symlink_to(self.path)
        with self.assertRaises(PermissionError):
            MemoryStore(self.path)
        sidecar.unlink()
        self.path.parent.chmod(0o755)
        with self.assertRaises(PermissionError):
            MemoryStore(self.path)

    def test_symlink_parent_refused(self):
        target = Path(self.temp.name) / "real"
        target.mkdir(mode=0o700)
        link = Path(self.temp.name) / "linked"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(OSError):
            MemoryStore(link / "memory.sqlite3")
        self.assertFalse((target / "memory.sqlite3").exists())

    def run_cli(self, command, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(output):
            result = main(["--db", str(self.path), *command])
        return result, output.getvalue()

    def test_cancel_does_not_create_database(self):
        for command, answers in (
            (["add"], ["hello", "no"]),
            (["edit", "1"], ["hello", "y"]),
            (["delete", "1"], [""]),
            (["clear"], ["YES"]),
        ):
            self.assertEqual(self.run_cli(command, answers)[0], 0)
            self.assertFalse(self.path.exists())
        with (
            patch("builtins.input", side_effect=EOFError),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(main(["--db", str(self.path), "add"]), 1)
        self.assertFalse(self.path.exists())

    def test_cli_mutations_require_confirmation(self):
        self.assertEqual(self.run_cli(["add"], ["hello", "yes"])[0], 0)
        self.run_cli(["edit", "1"], ["changed", "no"])
        self.assertIn("hello", self.run_cli(["list"], [])[1])
        self.run_cli(["edit", "1"], ["changed", "yes"])
        self.assertIn("changed", self.run_cli(["list"], [])[1])
        self.run_cli(["delete", "1"], ["no"])
        self.assertIn("changed", self.run_cli(["list"], [])[1])
        self.run_cli(["delete", "1"], ["yes"])
        self.assertIn("No saved memories", self.run_cli(["list"], [])[1])
        self.run_cli(["add"], ["again", "yes"])
        self.run_cli(["clear"], ["no"])
        self.assertIn("again", self.run_cli(["list"], [])[1])
        self.run_cli(["clear"], ["yes"])
        self.assertIn("No saved memories", self.run_cli(["list"], [])[1])

    def test_import_and_help_do_not_create_default_storage(self):
        environment = dict(os.environ, HOME=self.temp.name)
        for args in (("-c", "import milu.memory"), ("-m", "milu.memory", "--help")):
            result = subprocess.run(
                [sys.executable, *args], env=environment, capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((Path(self.temp.name) / ".local").exists())

    def test_no_text_command_line_argument(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--db", str(self.path), "add", "secret"])
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
