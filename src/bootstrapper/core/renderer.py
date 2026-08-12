"""Turning a component's `files/` directory into rendered file actions.

Two substitution mechanisms, deliberately separate:

* **File contents** — Jinja2, but only for files ending in `.j2` (the suffix is
  stripped from the output name). Any other file is copied byte for byte, so
  binary assets and files that themselves contain `{{ }}` pass through intact.
* **Paths** — `__variable__` markers, e.g. `src/__package_name__/main.py.j2`.
  Jinja delimiters are avoided in path names because braces in directory names
  confuse shells, editors and git tooling.

Undefined variables are an error, not an empty string: a typo in a template
should fail the generation, not silently produce a broken project.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError

from .component import Component
from .errors import RenderError
from .plan import FileAction

TEMPLATE_SUFFIX = ".j2"
_PATH_VARIABLE = re.compile(r"__([a-z_][a-z0-9_]*)__")


def github_expression(expression: str) -> str:
    """Emit a GitHub Actions expression: `gh('secrets.TOKEN')` -> `${{ secrets.TOKEN }}`.

    Actions expressions start with `${{`, which Jinja would try to evaluate.
    Wrapping them in `{% raw %}` works but is fragile — a raw tag at the start of
    a line loses its indentation to `lstrip_blocks`, which silently breaks YAML.
    Going through a helper keeps workflow templates readable and indentation-safe.
    """
    return "${{ " + expression + " }}"


def build_environment() -> Environment:
    """The Jinja environment used for every template file."""
    environment = Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # we generate source code, not HTML
    )
    environment.globals["gh"] = github_expression
    return environment


def render_path(path: str, context: Mapping[str, Any]) -> str:
    """Substitute `__name__` markers in a relative path.

    Only markers naming a variable that actually exists are substituted, so
    Python's own dunder filenames — `__init__.py`, `__main__.py` — pass through
    untouched instead of being read as placeholders.
    """

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            return match.group(0)
        return str(context[key])

    rendered = _PATH_VARIABLE.sub(replace, path)
    if rendered.endswith(TEMPLATE_SUFFIX):
        rendered = rendered[: -len(TEMPLATE_SUFFIX)]
    return rendered


class Renderer:
    """Renders components into `FileAction`s. Never touches the destination."""

    def __init__(self, environment: Environment | None = None) -> None:
        self.environment = environment or build_environment()

    def render_component(
        self, component: Component, context: Mapping[str, Any]
    ) -> Iterator[FileAction]:
        if not component.has_files():
            return
        merged: dict[str, Any] = {**context, **component.context}
        root = component.files_dir
        for source in sorted(root.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(root).as_posix()
            destination = render_path(relative, merged)
            if component.skip is not None and component.skip(merged, destination):
                continue
            yield self._render_file(source, destination, component.id, merged)

    def _render_file(
        self, source: Path, destination: str, origin: str, context: Mapping[str, Any]
    ) -> FileAction:
        executable = source.stat().st_mode & 0o111 != 0
        if source.name.endswith(TEMPLATE_SUFFIX):
            try:
                template = self.environment.from_string(source.read_text(encoding="utf-8"))
                content = template.render(**context).encode("utf-8")
            except TemplateError as exc:
                raise RenderError(source.name, str(exc)) from exc
            except UnicodeDecodeError as exc:
                raise RenderError(source.name, f"not valid UTF-8: {exc}") from exc
        else:
            content = source.read_bytes()
        return FileAction(path=destination, content=content, origin=origin, executable=executable)
