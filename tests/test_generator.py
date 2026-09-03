"""End-to-end generation of the built-in template.

These tests are the reason the templates can be edited with confidence: every
generated Python file is compiled and every generated workflow is parsed, so a
broken Jinja conditional fails here rather than in someone's new repository.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bootstrapper.core import Database, ProjectSpec, build_plan, generate


def _plan_paths(**kwargs: object) -> set[str]:
    spec = ProjectSpec(name="Market API", **kwargs)  # type: ignore[arg-type]
    return set(build_plan(spec).paths)


def test_default_selection_produces_a_complete_project() -> None:
    paths = _plan_paths(addons=["docker", "github-actions", "pre-commit", "ai-assistant"])

    assert {
        "pyproject.toml",
        "README.md",
        "Makefile",
        "LICENSE",
        ".gitignore",
        ".env.example",
        "src/market_api/main.py",
        "src/market_api/core/config.py",
        "src/market_api/api/routes/health.py",
        "src/market_api/db/session.py",
        "src/market_api/models/item.py",
        "migrations/env.py",
        "alembic.ini",
        "tests/conftest.py",
        "Dockerfile",
        "docker-compose.yml",
        ".github/workflows/ci.yml",
        ".pre-commit-config.yaml",
        "AGENTS.md",
        "CLAUDE.md",
    } <= paths


def test_no_database_drops_the_whole_persistence_layer() -> None:
    paths = _plan_paths(database=Database.none)

    assert not [path for path in paths if path.startswith(("migrations/", "src/market_api/db/"))]
    assert "alembic.ini" not in paths
    assert "src/market_api/models/item.py" not in paths
    assert "tests/test_items.py" not in paths
    # The service itself is still there.
    assert "src/market_api/main.py" in paths
    assert "tests/test_health.py" in paths


def test_addons_only_contribute_their_own_files() -> None:
    without = _plan_paths(addons=[])
    with_docker = _plan_paths(addons=["docker"])

    assert with_docker - without == {"Dockerfile", "docker-compose.yml", ".dockerignore"}


def test_ai_assistant_addon_describes_the_project() -> None:
    spec = ProjectSpec(name="Market API", addons=["pre-commit", "ai-assistant"])
    plan = build_plan(spec)

    claude_md = plan.actions["CLAUDE.md"].text
    agents_md = plan.actions["AGENTS.md"].text

    # CLAUDE.md defers to AGENTS.md rather than duplicating it.
    assert claude_md.strip() == "@AGENTS.md"
    assert "make check" in agents_md
    assert "pre-commit install" in agents_md  # only present because pre-commit is selected
    assert "MARKET_API_" in agents_md


def test_ai_assistant_addon_omits_addon_specific_sections_when_not_selected() -> None:
    spec = ProjectSpec(name="Market API", addons=["ai-assistant"])
    agents_md = build_plan(spec).actions["AGENTS.md"].text

    assert "pre-commit install" not in agents_md


@pytest.mark.parametrize("database", list(Database))
@pytest.mark.parametrize(
    "addons",
    [
        [],
        ["docker"],
        ["docker", "github-actions", "pre-commit"],
        ["deploy-ghcr"],
        ["deploy-azure-aca"],
        ["deploy-fly"],
    ],
)
def test_every_combination_renders_valid_python(database: Database, addons: list[str]) -> None:
    spec = ProjectSpec(name="Market API", database=database, addons=addons)

    for action in build_plan(spec):
        if action.path.endswith(".py"):
            compile(action.text, action.path, "exec")


@pytest.mark.parametrize("database", list(Database))
@pytest.mark.parametrize(
    "addons",
    [
        ["docker", "github-actions"],
        ["deploy-ghcr"],
        ["deploy-azure-aca"],
        ["deploy-fly"],
    ],
)
def test_every_combination_renders_parseable_yaml(database: Database, addons: list[str]) -> None:
    spec = ProjectSpec(name="Market API", database=database, addons=addons)

    workflows = 0
    for action in build_plan(spec):
        if action.path.endswith((".yml", ".yaml")):
            document = yaml.safe_load(action.text)
            assert isinstance(document, dict), action.path
            if action.path.startswith(".github/workflows/"):
                workflows += 1
                assert document["jobs"], action.path
    assert workflows >= 1


def test_github_actions_expressions_survive_rendering() -> None:
    spec = ProjectSpec(name="Market API", addons=["docker", "github-actions", "deploy-ghcr"])
    plan = build_plan(spec)

    publish = plan.actions[".github/workflows/publish.yml"].text

    # `${{ ... }}` must reach the file intact rather than being eaten by Jinja.
    assert "${{ secrets.GITHUB_TOKEN }}" in publish
    assert "${{ github.repository }}" in publish
    # docker/metadata-action has its own `{{version}}` syntax that must survive too.
    assert "type=semver,pattern={{version}}" in publish
    assert "{%" not in publish  # no unrendered Jinja tags left behind
    # Indentation is intact: no expression got flattened to column zero.
    assert "\n${{" not in publish


def test_project_name_reaches_the_generated_sources() -> None:
    plan = build_plan(ProjectSpec(name="Market API", addons=["docker"]))

    assert 'app_name: str = "Market API"' in plan.actions["src/market_api/core/config.py"].text
    assert 'env_prefix="MARKET_API_"' in plan.actions["src/market_api/core/config.py"].text
    assert "market_api.main:app" in plan.actions["Dockerfile"].text
    assert plan.actions["README.md"].text.startswith("# Market API")


def test_generate_writes_to_disk(tmp_path: Path) -> None:
    spec = ProjectSpec(name="Market API", git_init=False)

    result = generate(spec, tmp_path / "market-api")

    assert result.created
    assert (tmp_path / "market-api" / "pyproject.toml").is_file()
    assert len(result.written) == len(result.plan)


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    spec = ProjectSpec(name="Market API", git_init=False)

    result = generate(spec, tmp_path / "market-api", dry_run=True)

    assert result.written == []
    assert len(result.plan) > 0
    assert not (tmp_path / "market-api").exists()


def test_generate_initialises_git(tmp_path: Path) -> None:
    spec = ProjectSpec(name="Market API", git_init=True)

    result = generate(spec, tmp_path / "market-api")

    assert result.git is not None
    # git may be absent or unconfigured in a sandbox; either it worked or it said why.
    assert result.git.initialized or result.git.warnings
