"""The `ProjectSpec`: the single description of a project to generate.

This model is the contract between every front end and the generator. The CLI
builds one from flags and prompts; a web UI would build the same object from a
form and POST it as JSON. Nothing downstream of this module knows which one it
was.

Because it is a plain pydantic model it also gives us, for free:
  * validation with good error messages (`bootstrapper new --spec file.json`)
  * a JSON Schema a UI can render a form from (`bootstrapper schema`)
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from . import naming
from .errors import BootstrapperError

DEFAULT_TEMPLATE = "python-service"


class Database(StrEnum):
    """Which database the generated project talks to."""

    postgres = "postgres"
    sqlite = "sqlite"
    none = "none"


class License(StrEnum):
    mit = "MIT"
    apache2 = "Apache-2.0"
    proprietary = "proprietary"


class ProjectSpec(BaseModel):
    """Everything needed to render a project, and nothing else."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    name: str = Field(description="Human readable project name, e.g. 'Market API'")
    template: str = Field(default=DEFAULT_TEMPLATE, description="Registered template id")
    addons: list[str] = Field(
        default_factory=list, description="Registered addon ids layered on the template"
    )

    description: str = Field(default="", description="One line summary for README and packaging")
    author: str = Field(default="", description="Author name for packaging metadata")
    author_email: str = Field(default="", description="Author email for packaging metadata")
    license: License = Field(default=License.mit, description="License of the generated project")

    python_version: str = Field(default="3.12", description="Python version the project targets")
    database: Database = Field(default=Database.postgres, description="Database backend")

    github_owner: str = Field(default="", description="GitHub user or org that will host the repo")
    default_branch: str = Field(default="main", description="Default git branch name")
    git_init: bool = Field(default=True, description="Run `git init` and an initial commit")

    @field_validator("name")
    @classmethod
    def _name_must_slugify(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty")
        if not naming.slugify(value):
            raise ValueError(f"name {value!r} contains no usable characters")
        return value

    @field_validator("python_version")
    @classmethod
    def _python_version_shape(cls, value: str) -> str:
        parts = value.split(".")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("python_version must look like '3.12'")
        return value

    @field_validator("addons")
    @classmethod
    def _addons_unique(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for addon in value:
            if addon not in seen:
                seen.append(addon)
        return seen

    # --- derived values, exposed so templates and UIs never re-derive them ---

    @computed_field  # type: ignore[prop-decorator]
    @property
    def slug(self) -> str:
        """Directory and repository name, e.g. `market-api`."""
        return naming.slugify(self.name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def package_name(self) -> str:
        """Importable Python package, e.g. `market_api`."""
        return naming.package_name(self.name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def class_prefix(self) -> str:
        """Prefix for generated class names, e.g. `MarketApi`."""
        return naming.class_prefix(self.name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def env_prefix(self) -> str:
        """Settings env var prefix, e.g. `MARKET_API_`."""
        return naming.env_prefix(self.name)

    @property
    def uses_database(self) -> bool:
        return self.database is not Database.none

    def context(self) -> dict[str, Any]:
        """The variable namespace handed to Jinja."""
        data = self.model_dump(mode="json")
        data["uses_database"] = self.uses_database
        data["addons_enabled"] = dict.fromkeys(self.addons, True)
        data["has_addon"] = lambda addon: addon in self.addons
        return data

    @classmethod
    def from_file(cls, path: Path) -> ProjectSpec:
        """Load a spec from JSON on disk — the same payload a UI would POST."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:  # unreadable file
            raise BootstrapperError(f"cannot read spec {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise BootstrapperError(f"spec {path} is not valid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise BootstrapperError(f"spec {path} must contain a JSON object")
        # Computed fields are re-derived; accept and ignore them so a spec
        # round-trips through `bootstrapper new --print-spec`.
        for derived in ("slug", "package_name", "class_prefix", "env_prefix"):
            raw.pop(derived, None)
        return cls.model_validate(raw)
