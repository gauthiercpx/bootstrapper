"""Local git hooks, so CI is not the first thing to notice a formatting slip."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="pre-commit",
    summary="pre-commit config running ruff and the standard hygiene hooks.",
    root=Path(__file__).parent,
    order=30,
)

COMPONENTS = [ADDON]
