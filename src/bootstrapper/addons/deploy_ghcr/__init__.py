"""Publish the container image to the GitHub Container Registry."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="deploy-ghcr",
    summary="Build and push the image to ghcr.io on push to the default branch and on tags.",
    root=Path(__file__).parent,
    requires=("docker", "github-actions"),
    group="deploy",
    order=40,
)

COMPONENTS = [ADDON]
