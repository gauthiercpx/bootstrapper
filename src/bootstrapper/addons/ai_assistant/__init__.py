"""AI assistant context so an agent working in the generated repo starts informed
instead of guessing commands and conventions from scratch."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="ai-assistant",
    summary="CLAUDE.md and AGENTS.md describing project commands and conventions.",
    root=Path(__file__).parent,
    order=35,
)

COMPONENTS = [ADDON]
