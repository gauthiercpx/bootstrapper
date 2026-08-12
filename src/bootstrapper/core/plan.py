"""The generation plan.

Rendering is split in two phases on purpose:

  1. build a `Plan` — an in-memory list of files with their final content;
  2. `apply()` it to disk.

That split is what makes `--dry-run` honest (it runs the real render and only
skips the write), makes the engine testable without a filesystem, and lets a
future UI show a diff before anything is created.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .errors import TargetExists


@dataclass(frozen=True)
class FileAction:
    """One file to write, already rendered."""

    path: str
    """Destination path relative to the project root, using `/` separators."""

    content: bytes
    origin: str = ""
    """Which component produced it — used for conflict reporting."""

    executable: bool = False

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass
class Plan:
    """An ordered set of file actions, keyed by destination path."""

    actions: dict[str, FileAction] = field(default_factory=dict)
    overrides: list[tuple[str, str, str]] = field(default_factory=list)
    """(path, previous origin, new origin) for every intentional override."""

    def add(self, action: FileAction) -> None:
        """Add a file. A later component intentionally overrides an earlier one."""
        existing = self.actions.get(action.path)
        if existing is not None:
            self.overrides.append((action.path, existing.origin, action.origin))
        self.actions[action.path] = action

    def __iter__(self) -> Iterator[FileAction]:
        return iter(sorted(self.actions.values(), key=lambda action: action.path))

    def __len__(self) -> int:
        return len(self.actions)

    @property
    def paths(self) -> list[str]:
        return sorted(self.actions)

    def conflicts_in(self, destination: Path) -> list[str]:
        """Paths that already exist on disk and would be overwritten."""
        return [action.path for action in self if (destination / action.path).exists()]

    def apply(self, destination: Path, *, force: bool = False) -> list[Path]:
        """Write every file. Nothing is written if any conflict exists."""
        if not force:
            conflicts = self.conflicts_in(destination)
            if conflicts:
                preview = ", ".join(conflicts[:5])
                extra = f" (+{len(conflicts) - 5} more)" if len(conflicts) > 5 else ""
                raise TargetExists(
                    f"{destination} already contains {len(conflicts)} generated "
                    f"path(s): {preview}{extra}. Re-run with --force to overwrite."
                )

        written: list[Path] = []
        for action in self:
            target = destination / action.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(action.content)
            if action.executable:
                target.chmod(target.stat().st_mode | 0o111)
            written.append(target)
        return written

    def tree(self) -> str:
        """An indented view of the plan, for `--dry-run` output."""
        lines: list[str] = []
        seen_dirs: set[str] = set()
        for path in self.paths:
            parts = path.split("/")
            for depth in range(len(parts) - 1):
                directory = "/".join(parts[: depth + 1])
                if directory not in seen_dirs:
                    seen_dirs.add(directory)
                    lines.append(f"{'  ' * depth}{parts[depth]}/")
            lines.append(f"{'  ' * (len(parts) - 1)}{parts[-1]}")
        return os.linesep.join(lines)
