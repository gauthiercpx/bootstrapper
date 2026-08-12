"""Rendering rules: `.j2` contents, `__marker__` paths, raw passthrough."""

from __future__ import annotations

from pathlib import Path

import pytest

from bootstrapper.core import Component, Renderer, RenderError
from bootstrapper.core.renderer import render_path


def _component(tmp_path: Path, files: dict[str, str]) -> Component:
    for relative, content in files.items():
        target = tmp_path / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return Component(id="demo", summary="", root=tmp_path)


def test_path_markers_are_substituted() -> None:
    assert render_path("src/__package_name__/main.py.j2", {"package_name": "app"}) == (
        "src/app/main.py"
    )


def test_dunder_filenames_are_left_alone() -> None:
    # `__init__` is not a variable; treating it as one would break every package.
    assert render_path("src/__package_name__/__init__.py.j2", {"package_name": "app"}) == (
        "src/app/__init__.py"
    )


def test_j2_files_are_rendered_and_others_copied(tmp_path: Path) -> None:
    component = _component(
        tmp_path,
        {
            "greeting.txt.j2": "hello {{ name }}\n",
            "verbatim.txt": "left {{ name }} alone\n",
        },
    )

    actions = {
        action.path: action for action in Renderer().render_component(component, {"name": "x"})
    }

    assert actions["greeting.txt"].text == "hello x\n"
    assert actions["verbatim.txt"].text == "left {{ name }} alone\n"


def test_undefined_variables_fail_loudly(tmp_path: Path) -> None:
    component = _component(tmp_path, {"broken.txt.j2": "{{ nope }}"})

    with pytest.raises(RenderError, match="broken.txt.j2"):
        list(Renderer().render_component(component, {}))


def test_skip_predicate_drops_files(tmp_path: Path) -> None:
    component = _component(tmp_path, {"keep.txt": "a", "drop.txt": "b"})
    filtered = Component(
        id=component.id,
        summary="",
        root=tmp_path,
        skip=lambda _context, path: path == "drop.txt",
    )

    paths = [action.path for action in Renderer().render_component(filtered, {})]

    assert paths == ["keep.txt"]


def test_component_context_overrides_the_shared_namespace(tmp_path: Path) -> None:
    component = Component(id="demo", summary="", root=tmp_path, context={"name": "component wins"})
    _component(tmp_path, {"out.txt.j2": "{{ name }}"})

    actions = list(Renderer().render_component(component, {"name": "shared"}))

    assert actions[0].text == "component wins"


def test_binary_files_survive(tmp_path: Path) -> None:
    (tmp_path / "files").mkdir()
    payload = bytes(range(256))
    (tmp_path / "files" / "logo.bin").write_bytes(payload)
    component = Component(id="demo", summary="", root=tmp_path)

    actions = list(Renderer().render_component(component, {}))

    assert actions[0].content == payload
