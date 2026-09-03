"""The CLI surface: what a user actually types."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bootstrapper.cli import _report_result, _spec_from_flags, app
from bootstrapper.core import BootstrapperError, FileAction, GenerationResult, Plan, ProjectSpec

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


def test_missing_name_in_interactive_mode_is_prompted(monkeypatch: pytest.MonkeyPatch) -> None:
    from bootstrapper import cli

    monkeypatch.setattr(cli.typer, "prompt", lambda _: "Prompted Project")

    spec = _spec_from_flags(
        cli._registry(),
        name=None,
        template="python-service",
        addon=None,
        no_default_addons=True,
        database=None,
        python_version="3.12",
        description="",
        author="",
        author_email="",
        license_=cli.License.mit,
        github_owner="",
        default_branch="main",
        no_git=True,
        interactive=True,
    )

    assert spec.name == "Prompted Project"


def test_report_result_mentions_plan_overrides(capsys: pytest.CaptureFixture[str]) -> None:
    spec = ProjectSpec(name="Market API")
    plan = Plan()
    plan.add(FileAction(path="README.md", content=b"base", origin="template"))
    plan.add(FileAction(path="README.md", content=b"addon", origin="docker"))
    result = GenerationResult(spec=spec, destination=Path("market-api"), plan=plan, written=[])

    _report_result(spec, Path("market-api"), result)

    assert "README.md: docker overrode template" in capsys.readouterr().out


def test_schema_is_json(tmp_path: Path) -> None:
    target = tmp_path / "schema.json"

    result = runner.invoke(app, ["schema", "-o", str(target)])

    assert result.exit_code == 0
    assert "name" in json.loads(target.read_text())["properties"]


def test_schema_prints_to_stdout_without_output(tmp_path: Path) -> None:
    result = runner.invoke(app, ["schema"])

    assert result.exit_code == 0
    assert "name" in json.loads(result.output)["properties"]


def test_version_prints_something() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.output.strip()


def test_new_with_owner_suggests_gh_repo_create(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["new", "Market API", "-o", str(tmp_path), "--no-git", "--yes", "--owner", "gauthiercpx"],
    )

    assert result.exit_code == 0, result.output
    assert "gh repo create gauthiercpx/market-api" in result.output


def test_new_reports_git_steps(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "Market API", "-o", str(tmp_path), "--yes"])

    assert result.exit_code == 0, result.output
    # Either it initialised the repo, or it said why not -- both are reported.
    assert "git init" in result.output or "!" in result.output


def test_main_turns_bootstrapper_errors_into_a_clean_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    from bootstrapper import cli

    def boom() -> None:
        raise BootstrapperError("boom")

    monkeypatch.setattr(cli, "app", boom)

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1
