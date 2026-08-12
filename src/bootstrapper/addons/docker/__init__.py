"""Container image and a local stack that includes the database."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="docker",
    summary="Multi-stage Dockerfile, docker-compose stack and .dockerignore.",
    root=Path(__file__).parent,
    order=10,
)

COMPONENTS = [ADDON]
