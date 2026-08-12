"""Name derivation helpers.

A single project name typed by a human has to become several different
identifiers: a directory name, a Python package, a Docker image tag, a class
prefix. All of those derivations live here so the CLI, the templates and any
future UI agree on them.
"""

from __future__ import annotations

import keyword
import re
import unicodedata

_SEPARATORS = re.compile(r"[\s._/\\-]+")
_INVALID_SLUG_CHARS = re.compile(r"[^a-z0-9-]")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _ascii_fold(value: str) -> str:
    """Strip accents so "créditagricole" and "creditagricole" slug identically."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def words(value: str) -> list[str]:
    """Split an arbitrary human name into lowercase word tokens."""
    spaced = _CAMEL_BOUNDARY.sub(" ", _ascii_fold(value))
    tokens = _SEPARATORS.split(spaced)
    return [re.sub(r"[^a-zA-Z0-9]", "", token).lower() for token in tokens if token.strip()]


def slugify(value: str) -> str:
    """`My Cool API` -> `my-cool-api`. Used for the directory and repo name."""
    slug = "-".join(words(value))
    slug = _INVALID_SLUG_CHARS.sub("", slug).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def package_name(value: str) -> str:
    """`My Cool API` -> `my_cool_api`, guaranteed importable."""
    name = "_".join(words(value))
    if not name:
        return "app"
    if name[0].isdigit():
        name = f"_{name}"
    if keyword.iskeyword(name):
        name = f"{name}_"
    return name


def class_prefix(value: str) -> str:
    """`My Cool API` -> `MyCoolApi`. Handy for generated class names."""
    return "".join(token.capitalize() for token in words(value)) or "App"


def env_prefix(value: str) -> str:
    """`My Cool API` -> `MY_COOL_API_`. Used for settings env var namespacing."""
    return f"{'_'.join(words(value)).upper()}_" if words(value) else "APP_"
