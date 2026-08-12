"""The spec is the contract between front ends, so its edges are worth pinning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bootstrapper.core import Database, ProjectSpec


def test_derived_names_are_exposed() -> None:
    spec = ProjectSpec(name="Market API")

    assert spec.slug == "market-api"
    assert spec.package_name == "market_api"
    assert spec.class_prefix == "MarketApi"
    assert spec.env_prefix == "MARKET_API_"


def test_empty_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectSpec(name="   ")


def test_name_without_usable_characters_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectSpec(name="---")


def test_unknown_field_is_rejected() -> None:
    # A UI posting a stale field should get an error, not silent data loss.
    with pytest.raises(ValidationError):
        ProjectSpec.model_validate({"name": "Market API", "databse": "postgres"})


def test_bad_python_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectSpec(name="Market API", python_version="3")


def test_duplicate_addons_collapse() -> None:
    spec = ProjectSpec(name="Market API", addons=["docker", "docker", "pre-commit"])

    assert spec.addons == ["docker", "pre-commit"]


def test_uses_database_follows_the_choice() -> None:
    assert ProjectSpec(name="A").uses_database is True
    assert ProjectSpec(name="A", database=Database.none).uses_database is False


def test_spec_round_trips_through_json(tmp_path: Path) -> None:
    original = ProjectSpec(name="Market API", database=Database.sqlite, addons=["docker"])
    path = tmp_path / "spec.json"
    # Includes the computed fields, exactly like `new --print-spec` emits.
    path.write_text(original.model_dump_json(), encoding="utf-8")

    assert ProjectSpec.from_file(path) == original


def test_invalid_json_reports_the_file(tmp_path: Path) -> None:
    path = tmp_path / "spec.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(Exception, match="not valid JSON"):
        ProjectSpec.from_file(path)


def test_schema_is_renderable_by_a_form() -> None:
    schema = ProjectSpec.model_json_schema()
    payload = json.dumps(schema)  # must be serialisable to hand to a UI

    assert "name" in schema["required"]
    assert "template" in schema["properties"]
    assert len(payload) > 0
