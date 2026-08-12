"""The generation engine.

Front ends (the CLI today, an HTTP API tomorrow) should import from here and
from nowhere deeper, so the internals stay free to move.
"""

from __future__ import annotations

from .component import Addon, Component, Template
from .errors import (
    BootstrapperError,
    IncompatibleSelection,
    RenderError,
    TargetExists,
    UnknownComponent,
)
from .generator import GenerationResult, build_plan, components_for, generate
from .plan import FileAction, Plan
from .registry import Registry, default_registry
from .renderer import Renderer
from .spec import Database, License, ProjectSpec
from .vcs import GitResult, create_github_repository, init_repository

__all__ = [
    "Addon",
    "BootstrapperError",
    "Component",
    "Database",
    "FileAction",
    "GenerationResult",
    "GitResult",
    "IncompatibleSelection",
    "License",
    "Plan",
    "ProjectSpec",
    "Registry",
    "RenderError",
    "Renderer",
    "TargetExists",
    "Template",
    "UnknownComponent",
    "build_plan",
    "components_for",
    "create_github_repository",
    "default_registry",
    "generate",
    "init_repository",
]
