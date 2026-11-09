"""Explicit, local-only memory. Importing this module never creates files.

CLI: python -m milu.memory [--db PATH] {list,add,edit ID,delete ID,clear}
Text is prompted, never accepted as a command-line argument. Mutations require
literal ``yes``. Limits: 1,000 entries, 4,096 Unicode characters per entry.
This is not encrypted storage. SQLite secure_delete cannot erase filesystem
snapshots, backups, flash wear-leveling copies, or previously exported data.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_ENTRIES = 1000
MAX_TEXT_LENGTH = 4096


@dataclass(frozen=True)
class MemoryRecord:
    id: int
    text: str
    created_at: str
    updated_at: str


def _private_database(path: Path) -> Path:
    """Create private paths without following symlinks or changing permissions."""
    path = Path(os.path.abspath(path.expanduser()))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(path.anchor, flags)
    try:
        for component in path.parent.parts[1:]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=directory)
            except FileExistsError:
                pass
            child = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            # /tmp is allowed as an ancestor, but never as the database parent.
            if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                raise PermissionError("Database ancestors must not be writable by others")
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise PermissionError("Database parent must be owned by you with permissions 0700")
        try:
            fd = os.open(
                path.name,
                os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
        except FileExistsError:
            fd = os.open(path.name, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1
            ):
                raise PermissionError(
                    "Database must be a private, singly linked regular file (0600)"
                )
        finally:
            os.close(fd)
        for suffix in ("-journal", "-wal", "-shm"):
            try:
                info = os.stat(path.name + suffix, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1
            ):
                raise PermissionError("Unsafe SQLite sidecar file")
    finally:
        os.close(directory)
    return path


def _validate_text(text: str) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Memory text must not be empty")
    if len(text) > MAX_TEXT_LENGTH or "\x00" in text:
        raise ValueError(f"Memory text must be at most {MAX_TEXT_LENGTH} characters, without NUL")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    """Construct only for an explicit memory operation, never on app startup."""

    def __init__(self, path: Path):
        self.path = _private_database(path)
        self._connection = sqlite3.connect(self.path, timeout=5)
        self._connection.row_factory = sqlite3.Row
        try:
            self._connection.execute("PRAGMA secure_delete = ON")
            self._connection.execute("PRAGMA journal_mode = DELETE")
            with self._connection:
                self._connection.execute(
                    "CREATE TABLE IF NOT EXISTS memories ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, "
                    "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
                )
        except Exception:
            self.close()
            raise

    def add(self, text: str) -> int:
        _validate_text(text)
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if (
                self._connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                >= MAX_ENTRIES
            ):
                raise ValueError(f"Memory limit reached ({MAX_ENTRIES} entries)")
            timestamp = _now()
            cursor = self._connection.execute(
                "INSERT INTO memories (text, created_at, updated_at) VALUES (?, ?, ?)",
                (text, timestamp, timestamp),
            )
            return int(cursor.lastrowid)

    def list(self) -> list[MemoryRecord]:
        return [
            MemoryRecord(**dict(row))
            for row in self._connection.execute("SELECT * FROM memories ORDER BY id")
        ]

    def get(self, id: int) -> MemoryRecord | None:
        row = self._connection.execute("SELECT * FROM memories WHERE id = ?", (id,)).fetchone()
        return MemoryRecord(**dict(row)) if row else None

    def update(self, id: int, text: str) -> bool:
        _validate_text(text)
        with self._connection:
            return (
                self._connection.execute(
                    "UPDATE memories SET text = ?, updated_at = ? WHERE id = ?", (text, _now(), id)
                ).rowcount
                > 0
            )

    def delete(self, id: int) -> bool:
        with self._connection:
            return self._connection.execute("DELETE FROM memories WHERE id = ?", (id,)).rowcount > 0

    def clear(self) -> int:
        with self._connection:
            return self._connection.execute("DELETE FROM memories").rowcount

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path.home() / ".local/share/milu/memory.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("add")
    for command in ("edit", "delete"):
        commands.add_parser(command).add_argument("id", type=int)
    commands.add_parser("clear")
    args = parser.parse_args(argv)
    try:
        text = None
        if args.command in ("add", "edit"):
            text = input("Memory text (local, unencrypted; do not enter secrets): ")
            _validate_text(text)
        if args.command != "list":
            if input(f"Confirm {args.command}: type yes to continue: ").strip() != "yes":
                print("Cancelled; no changes made.")
                return 0
        with MemoryStore(args.db) as store:
            if args.command == "list":
                records = store.list()
                for record in records:
                    # repr escapes terminal control characters in user-supplied text.
                    print(f"{record.id}: {record.text!r}")
                if not records:
                    print("No saved memories.")
            elif args.command == "add":
                print(f"Saved memory {store.add(text)}.")
            elif args.command == "edit":
                print("Updated." if store.update(args.id, text) else "Memory not found.")
            elif args.command == "delete":
                print("Deleted." if store.delete(args.id) else "Memory not found.")
            else:
                print(f"Deleted {store.clear()} memories.")
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"Memory operation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
