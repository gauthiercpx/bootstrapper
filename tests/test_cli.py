"""The CLI surface: what a user actually types."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bootstrapper.cli import app

runner = CliRunner()


def test_list_templates_mentions_the_builtin() -> None:
    result = runner.invoke(app, ["list", "templates"])

    assert result.exit_code == 0
    assert "python-service" in result.output


def test_list_addons_can_be_filtered_by_template() -> None:
    result = runner.invoke(app, ["list", "addons", "--template", "python-service"])

    assert result.exit_code == 0
    assert "docker" in result.output


def test_describe_shows_defaults() -> None:
    result = runner.invoke(app, ["describe", "python-service"])

    assert result.exit_code == 0
    assert "default addons" in result.output


def test_describe_unknown_template_fails_cleanly() -> None:
    result = runner.invoke(app, ["describe", "nope"])

    assert result.exit_code != 0
    assert "unknown template" in str(result.exception) or "unknown template" in result.output


def test_new_creates_the_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "Market API", "-o", str(tmp_path), "--no-git", "--yes"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "market-api" / "pyproject.toml").is_file()
    # Template defaults applied without being asked for.
    assert (tmp_path / "market-api" / "Dockerfile").is_file()


def test_no_default_addons_starts_empty(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["new", "Market API", "-o", str(tmp_path), "--no-default-addons", "--no-git", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "market-api" / "Dockerfile").exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "Market API", "-o", str(tmp_path), "--dry-run", "--yes"])

    assert result.exit_code == 0
    assert "dry run" in result.output
    assert not (tmp_path / "market-api").exists()


def test_rerunning_without_force_refuses(tmp_path: Path) -> None:
    args = ["new", "Market API", "-o", str(tmp_path), "--no-git", "--yes"]
    assert runner.invoke(app, args).exit_code == 0

    second = runner.invoke(app, args)

    assert second.exit_code != 0
    assert "--force" in str(second.exception)


def test_print_spec_round_trips(tmp_path: Path) -> None:
    printed = runner.invoke(
        app,
        ["new", "Market API", "--db", "sqlite", "--print-spec", "--yes"],
    )
    assert printed.exit_code == 0, printed.output
    # Rich pretty-prints JSON; the payload is still the whole output.
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(printed.output, encoding="utf-8")
    assert json.loads(printed.output)["database"] == "sqlite"

    generated = runner.invoke(
        app, ["new", "--spec", str(spec_path), "-o", str(tmp_path), "--no-git", "--yes"]
    )

    assert generated.exit_code == 0, generated.output
    assert (tmp_path / "market-api" / "pyproject.toml").is_file()


def test_conflicting_deploy_addons_are_refused(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "new",
            "Market API",
            "-o",
            str(tmp_path),
            "-a",
            "deploy-fly",
            "-a",
            "deploy-ghcr",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "only one 'deploy'" in str(result.exception)


def test_missing_name_without_a_tty_is_an_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "-o", str(tmp_path), "--yes"])

    assert result.exit_code != 0


def test_schema_is_json(tmp_path: Path) -> None:
    target = tmp_path / "schema.json"

    result = runner.invoke(app, ["schema", "-o", str(target)])

    assert result.exit_code == 0
    assert "name" in json.loads(target.read_text())["properties"]
