"""The `python-service` template: a FastAPI service wired to a database.

What it generates:
  * FastAPI app with settings, structured logging and a real `/health` endpoint
  * async SQLAlchemy 2.0 session management and one worked-through CRUD resource
  * Alembic migrations configured against the same async engine
  * pytest suite that runs against SQLite in-memory, so `make test` works with
    no services running
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bootstrapper.core.component import Template

_ROOT = Path(__file__).parent


def _skip(context: Mapping[str, Any], path: str) -> bool:
    """Drop the persistence layer entirely when the project has no database."""
    if context.get("uses_database"):
        return False
    package = context["package_name"]
    database_only = (
        "alembic.ini",
        "migrations/",
        f"src/{package}/db/",
        f"src/{package}/models/",
        f"src/{package}/schemas/",
        f"src/{package}/api/routes/items.py",
        "tests/test_items.py",
    )
    return path.startswith(database_only)


TEMPLATE = Template(
    id="python-service",
    summary="FastAPI service with async SQLAlchemy, Alembic migrations and pytest.",
    root=_ROOT,
    language="python",
    order=0,
    default_addons=("docker", "github-actions", "pre-commit", "ai-assistant"),
    skip=_skip,
)

COMPONENTS = [TEMPLATE]
