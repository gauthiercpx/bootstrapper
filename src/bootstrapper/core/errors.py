"""Exception types shared by the core engine.

Every error the engine raises on purpose derives from `BootstrapperError`, so
the CLI can turn them into a clean message instead of a traceback, and a future
HTTP layer can map them to 4xx responses.
"""

from __future__ import annotations


class BootstrapperError(Exception):
    """Base class for every expected failure."""


class UnknownComponent(BootstrapperError):
    """A template or addon name was requested but is not registered."""

    def __init__(self, kind: str, name: str, available: list[str]) -> None:
        options = ", ".join(sorted(available)) or "none registered"
        super().__init__(f"unknown {kind} {name!r}. Available: {options}")
        self.kind = kind
        self.name = name
        self.available = available


class IncompatibleSelection(BootstrapperError):
    """The chosen addons cannot be combined, or do not fit the template."""


class TargetExists(BootstrapperError):
    """The output directory already holds files that would be overwritten."""


class RenderError(BootstrapperError):
    """A template file failed to render."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"failed to render {source}: {reason}")
        self.source = source
        self.reason = reason
