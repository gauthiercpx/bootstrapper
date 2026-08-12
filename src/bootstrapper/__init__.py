"""bootstrapper — modular project scaffolding.

`bootstrapper.core` holds the engine; `bootstrapper.cli` is one front end over
it. Templates and addons live in `bootstrapper.templates` and
`bootstrapper.addons`, and third-party packages can add more through entry
points.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
