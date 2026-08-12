"""Deploy to Fly.io."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="deploy-fly",
    summary="fly.toml plus a deploy workflow using FLY_API_TOKEN.",
    root=Path(__file__).parent,
    requires=("docker", "github-actions"),
    group="deploy",
    order=40,
)

COMPONENTS = [ADDON]
