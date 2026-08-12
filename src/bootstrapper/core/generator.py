"""Spec in, project on disk out.

This is the whole public surface of the engine. The CLI is a thin wrapper over
`build_plan` and `generate`; a web UI would call exactly the same two functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .component import Component
from .plan import Plan
from .registry import Registry, default_registry
from .renderer import Renderer
from .spec import ProjectSpec
from .vcs import GitResult, init_repository


def components_for(spec: ProjectSpec, registry: Registry) -> list[Component]:
    """The template followed by its resolved addons, in render order."""
    template = registry.template(spec.template)
    addons = registry.resolve(spec.template, spec.addons)
    return [template, *addons]


def build_plan(
    spec: ProjectSpec,
    registry: Registry | None = None,
    *,
    renderer: Renderer | None = None,
) -> Plan:
    """Render everything in memory. Does not touch the filesystem."""
    registry = registry or default_registry()
    renderer = renderer or Renderer()

    context: dict[str, Any] = spec.context()
    selected = components_for(spec, registry)
    context["components"] = [component.id for component in selected]

    plan = Plan()
    for component in selected:
        for action in renderer.render_component(component, context):
            plan.add(action)
    return plan


@dataclass
class GenerationResult:
    """What `generate` did, for the CLI and any UI to report on."""

    spec: ProjectSpec
    destination: Path
    plan: Plan
    written: list[Path]
    git: GitResult | None = None

    @property
    def created(self) -> bool:
        return bool(self.written)


def generate(
    spec: ProjectSpec,
    destination: Path,
    registry: Registry | None = None,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> GenerationResult:
    """Render `spec` into `destination`, optionally initialising a git repo."""
    plan = build_plan(spec, registry)

    if dry_run:
        return GenerationResult(spec=spec, destination=destination, plan=plan, written=[])

    destination.mkdir(parents=True, exist_ok=True)
    written = plan.apply(destination, force=force)

    git: GitResult | None = None
    if spec.git_init:
        git = init_repository(destination, branch=spec.default_branch)

    return GenerationResult(spec=spec, destination=destination, plan=plan, written=written, git=git)
