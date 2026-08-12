"""Continuous integration on GitHub Actions."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="github-actions",
    summary="CI workflow (lint, typecheck, tests) plus Dependabot.",
    root=Path(__file__).parent,
    order=20,
)

COMPONENTS = [ADDON]
