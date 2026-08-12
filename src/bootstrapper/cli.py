"""The command line front end.

This module holds presentation only — prompting, tables, colours, exit codes.
Every decision about *what* gets generated lives in `bootstrapper.core`, which
is what keeps a future web UI from having to reimplement any of it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .core import (
    BootstrapperError,
    Database,
    License,
    ProjectSpec,
    Registry,
    default_registry,
    generate,
)
from .core.spec import DEFAULT_TEMPLATE

console = Console()
error_console = Console(stderr=True)

app = typer.Typer(
    name="bootstrapper",
    help="Bootstrap new projects: repo skeleton, GitHub Actions and deployment.",
    no_args_is_help=True,
    add_completion=False,
)
list_app = typer.Typer(help="List what is available to generate.", no_args_is_help=True)
app.add_typer(list_app, name="list")


def _registry() -> Registry:
    return default_registry()


# --------------------------------------------------------------------------- #
# new
# --------------------------------------------------------------------------- #


@app.command()
def new(  # noqa: PLR0913 - a scaffolder command is inherently option-heavy
    name: Annotated[str | None, typer.Argument(help="Project name, e.g. 'Market API'.")] = None,
    template: Annotated[
        str, typer.Option("--template", "-t", help="Template to start from.")
    ] = DEFAULT_TEMPLATE,
    addon: Annotated[
        list[str] | None,
        typer.Option("--addon", "-a", help="Addon to include. Repeatable."),
    ] = None,
    no_default_addons: Annotated[
        bool, typer.Option("--no-default-addons", help="Start from an empty addon selection.")
    ] = False,
    database: Annotated[Database | None, typer.Option("--db", help="Database backend.")] = None,
    python_version: Annotated[
        str, typer.Option("--python", help="Python version the project targets.")
    ] = "3.12",
    description: Annotated[str, typer.Option("--description", help="One line summary.")] = "",
    author: Annotated[str, typer.Option("--author", help="Author name.")] = "",
    author_email: Annotated[str, typer.Option("--email", help="Author email.")] = "",
    license_: Annotated[
        License, typer.Option("--license", help="License of the generated project.")
    ] = License.mit,
    github_owner: Annotated[
        str, typer.Option("--owner", help="GitHub user or org that will host the repo.")
    ] = "",
    default_branch: Annotated[str, typer.Option("--branch", help="Default git branch.")] = "main",
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Directory the project is created in.")
    ] = Path(),
    spec_file: Annotated[
        Path | None,
        typer.Option("--spec", help="Read a JSON ProjectSpec instead of using flags."),
    ] = None,
    print_spec: Annotated[
        bool, typer.Option("--print-spec", help="Print the resolved spec as JSON and exit.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Render everything, write nothing.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite files that already exist.")
    ] = False,
    no_git: Annotated[bool, typer.Option("--no-git", help="Skip git init.")] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Never prompt; use defaults for anything missing.")
    ] = False,
) -> None:
    """Create a new project."""
    registry = _registry()
    interactive = not yes and sys.stdin.isatty()

    if spec_file is not None:
        spec = ProjectSpec.from_file(spec_file)
    else:
        if not name:
            if not interactive:
                raise typer.BadParameter("a project name is required (or pass --spec)")
            name = typer.prompt("Project name")
        selected = _resolve_addons(registry, template, addon, no_default_addons=no_default_addons)
        if database is None:
            database = Database.postgres
        spec = ProjectSpec(
            name=name,
            template=template,
            addons=selected,
            description=description,
            author=author,
            author_email=author_email,
            license=license_,
            python_version=python_version,
            database=database,
            github_owner=github_owner,
            default_branch=default_branch,
            git_init=not no_git,
        )

    if no_git:
        spec = spec.model_copy(update={"git_init": False})

    if print_spec:
        console.print_json(spec.model_dump_json(indent=2))
        raise typer.Exit(0)

    destination = (output / spec.slug).resolve()
    result = generate(spec, destination, registry, force=force, dry_run=dry_run)

    if dry_run:
        console.print(
            Panel(
                result.plan.tree(),
                title=f"[bold]{len(result.plan)} files[/bold] — dry run, nothing written",
                subtitle=str(destination),
                border_style="cyan",
            )
        )
        return

    console.print(
        f"[green]✓[/green] created [bold]{spec.name}[/bold] "
        f"({len(result.written)} files) in [cyan]{destination}[/cyan]"
    )
    if result.plan.overrides:
        for path, previous, new in result.plan.overrides:
            console.print(f"  [dim]{path}: {new} overrode {previous}[/dim]")
    if result.git is not None:
        for step in result.git.steps:
            console.print(f"  [dim]{step}[/dim]")
        for warning in result.git.warnings:
            console.print(f"  [yellow]![/yellow] {warning}")

    console.print(_next_steps(spec, destination))


def _resolve_addons(
    registry: Registry,
    template_id: str,
    requested: list[str] | None,
    *,
    no_default_addons: bool,
) -> list[str]:
    """Explicit `--addon` flags win; otherwise fall back to template defaults."""
    if requested:
        return list(requested)
    if no_default_addons:
        return []
    return list(registry.template(template_id).default_addons)


def _next_steps(spec: ProjectSpec, destination: Path) -> Panel:
    lines = [f"cd {destination.name}"]
    if spec.github_owner:
        lines.append(
            f"gh repo create {spec.github_owner}/{spec.slug} "
            "--public --source . --remote origin --push"
        )
    lines += ["make install", "make up" if spec.uses_database else "make run", "make test"]
    return Panel(
        "\n".join(f"[cyan]$[/cyan] {line}" for line in lines),
        title="next steps",
        border_style="green",
    )


# --------------------------------------------------------------------------- #
# list / describe / schema
# --------------------------------------------------------------------------- #


@list_app.command("templates")
def list_templates() -> None:
    """Show every registered template."""
    registry = _registry()
    table = Table(title="templates", header_style="bold")
    table.add_column("id", style="cyan")
    table.add_column("language")
    table.add_column("summary")
    table.add_column("default addons", style="dim")
    for template in sorted(registry.templates.values(), key=lambda item: item.id):
        table.add_row(
            template.id,
            template.language,
            template.summary,
            ", ".join(template.default_addons) or "-",
        )
    console.print(table)


@list_app.command("addons")
def list_addons(
    template: Annotated[
        str | None, typer.Option("--template", "-t", help="Only addons that fit this template.")
    ] = None,
) -> None:
    """Show every registered addon."""
    registry = _registry()
    addons = (
        registry.addons_for(template)
        if template
        else sorted(registry.addons.values(), key=lambda item: (item.order, item.id))
    )
    table = Table(title="addons", header_style="bold")
    table.add_column("id", style="cyan")
    table.add_column("group")
    table.add_column("summary")
    table.add_column("applies to", style="dim")
    for addon in addons:
        table.add_row(addon.id, addon.group or "-", addon.summary, ", ".join(addon.applies_to))
    console.print(table)


@app.command()
def describe(
    template: Annotated[str, typer.Argument(help="Template id.")],
) -> None:
    """Show a template's defaults and the addons compatible with it."""
    registry = _registry()
    found = registry.template(template)
    console.print(
        Panel(
            f"{found.summary}\n\n"
            f"language: {found.language}\n"
            f"default addons: {', '.join(found.default_addons) or '-'}",
            title=found.id,
            border_style="cyan",
        )
    )
    list_addons(template=template)


@app.command()
def schema(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write to a file instead of stdout.")
    ] = None,
) -> None:
    """Print the ProjectSpec JSON Schema — enough for a UI to render a form."""
    payload = json.dumps(ProjectSpec.model_json_schema(), indent=2)
    if output is not None:
        output.write_text(payload + "\n", encoding="utf-8")
        console.print(f"[green]✓[/green] wrote {output}")
    else:
        console.print_json(payload)


@app.command()
def version() -> None:
    """Print the bootstrapper version."""
    console.print(__version__)


def main() -> None:
    """Console script entry point: turn expected errors into clean messages."""
    try:
        app()
    except BootstrapperError as exc:
        error_console.print(f"[red]error:[/red] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover
    main()
