"""Selection resolution: requires, conflicts and exclusive groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from bootstrapper.core import (
    Addon,
    IncompatibleSelection,
    Registry,
    Template,
    UnknownComponent,
    default_registry,
)


def _registry(tmp_path: Path) -> Registry:
    registry = Registry()
    registry.register(Template(id="svc", summary="", root=tmp_path))
    registry.register(Template(id="lib", summary="", root=tmp_path))
    registry.register(Addon(id="docker", summary="", root=tmp_path, order=10))
    registry.register(Addon(id="ci", summary="", root=tmp_path, order=20))
    registry.register(
        Addon(
            id="deploy-a",
            summary="",
            root=tmp_path,
            requires=("docker", "ci"),
            group="deploy",
            order=40,
        )
    )
    registry.register(Addon(id="deploy-b", summary="", root=tmp_path, group="deploy", order=40))
    registry.register(Addon(id="svc-only", summary="", root=tmp_path, applies_to=("svc",)))
    registry.register(Addon(id="a", summary="", root=tmp_path, conflicts=("b",)))
    registry.register(Addon(id="b", summary="", root=tmp_path))
    return registry


def test_requires_are_pulled_in(tmp_path: Path) -> None:
    resolved = _registry(tmp_path).resolve("svc", ["deploy-a"])

    assert [addon.id for addon in resolved] == ["docker", "ci", "deploy-a"]


def test_resolution_is_ordered_by_render_order(tmp_path: Path) -> None:
    resolved = _registry(tmp_path).resolve("svc", ["ci", "docker"])

    assert [addon.id for addon in resolved] == ["docker", "ci"]


def test_two_addons_in_the_same_group_are_rejected(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    with pytest.raises(IncompatibleSelection, match="only one 'deploy'"):
        registry.resolve("svc", ["deploy-a", "deploy-b"])


def test_declared_conflicts_are_rejected(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    with pytest.raises(IncompatibleSelection, match="conflicts with"):
        registry.resolve("svc", ["a", "b"])


def test_addon_not_applicable_to_the_template_is_rejected(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    with pytest.raises(IncompatibleSelection, match="does not apply"):
        registry.resolve("lib", ["svc-only"])


def test_unknown_names_list_the_alternatives(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    with pytest.raises(UnknownComponent, match="Available:"):
        registry.resolve("svc", ["nope"])

    with pytest.raises(UnknownComponent, match="unknown template"):
        registry.template("nope")


def test_builtins_are_discovered() -> None:
    registry = default_registry()

    assert "python-service" in registry.templates
    assert {"docker", "github-actions", "pre-commit"} <= set(registry.addons)
    # Every default a template advertises must actually resolve.
    for template in registry.templates.values():
        registry.resolve(template.id, template.default_addons)


def test_every_builtin_deploy_addon_is_mutually_exclusive() -> None:
    registry = default_registry()
    deploys = [addon.id for addon in registry.addons.values() if addon.group == "deploy"]

    assert len(deploys) >= 2
    with pytest.raises(IncompatibleSelection):
        registry.resolve("python-service", deploys[:2])
