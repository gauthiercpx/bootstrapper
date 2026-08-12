"""Templates and addons — the two things the registry knows about.

A **template** is a complete starting point (a FastAPI service, a library, …).
An **addon** is a slice of a project that is worth choosing independently: CI
workflows, a Dockerfile, a deployment target, pre-commit hooks.

Both are the same shape: a directory of files to render, plus a little metadata.
Keeping them structurally identical is what makes the engine short — the
generator renders `[template, *addons]` in order and the later component wins on
a path collision.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ANY_TEMPLATE = "*"

SkipPredicate = Callable[[Mapping[str, Any], str], bool]
"""Given the render context and a relative path, return True to drop the file."""


@dataclass(frozen=True)
class Component:
    """A named directory of renderable files."""

    id: str
    summary: str
    root: Path
    """Directory holding this component's `files/` payload."""

    requires: tuple[str, ...] = ()
    """Addon ids that must also be selected."""

    conflicts: tuple[str, ...] = ()
    """Addon ids that cannot be selected alongside this one."""

    order: int = 100
    """Render order. Lower renders first; later components override earlier files."""

    context: Mapping[str, Any] = field(default_factory=dict)
    """Extra variables merged into the Jinja namespace while this component renders."""

    skip: SkipPredicate | None = None
    """Optional filter to drop files that do not apply to a given spec."""

    @property
    def files_dir(self) -> Path:
        return self.root / "files"

    def has_files(self) -> bool:
        return self.files_dir.is_dir()


@dataclass(frozen=True)
class Template(Component):
    """A complete project starting point."""

    language: str = "python"
    default_addons: tuple[str, ...] = ()
    """Addons enabled unless the caller passes an explicit selection."""


@dataclass(frozen=True)
class Addon(Component):
    """An optional slice layered on top of a template."""

    applies_to: tuple[str, ...] = (ANY_TEMPLATE,)
    group: str = ""
    """Addons sharing a non-empty group are mutually exclusive (e.g. `deploy`)."""

    def supports(self, template_id: str) -> bool:
        return ANY_TEMPLATE in self.applies_to or template_id in self.applies_to
