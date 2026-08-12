# Extending bootstrapper

Two seams, in increasing order of commitment: add a component to this repo, or
ship one from your own package.

## The two component kinds

| | Template | Addon |
| --- | --- | --- |
| what it is | a complete starting point | a slice layered on top |
| example | `python-service` | `docker`, `deploy-fly` |
| chosen with | `--template` (exactly one) | `--addon` (any number) |

They are the same dataclass underneath. The generator renders
`[template, *addons]` in `order`, and a later component writing to a path an
earlier one already wrote is a legitimate override — the CLI prints it rather
than hiding it.

## Adding one to this repo

1. Create the payload directory:

```
src/bootstrapper/templates/go_service/
  __init__.py
  files/
    go.mod.j2
    cmd/__slug__/main.go.j2
```

2. Declare the component in `__init__.py`:

```python
from pathlib import Path

from bootstrapper.core.component import Template

TEMPLATE = Template(
    id="go-service",
    summary="Go HTTP service with chi and pgx.",
    root=Path(__file__).parent,
    language="go",
    order=0,
    default_addons=("docker", "github-actions"),
)

COMPONENTS = [TEMPLATE]
```

The registry imports every submodule of `bootstrapper.templates` and
`bootstrapper.addons` at startup and collects each module's `COMPONENTS`. There
is no list to also remember to edit.

3. `tests/test_generator.py` renders every template across every database and
   addon combination, compiling generated Python and parsing generated YAML. A
   new template is covered by those tests the moment it is registered — add
   template-specific assertions for anything they cannot check generically.

## Shipping one from your own package

Register an entry point; nothing in this repo changes.

```toml
# your-package/pyproject.toml
[project.entry-points."bootstrapper.templates"]
go-service = "your_package.templates:COMPONENTS"

[project.entry-points."bootstrapper.addons"]
deploy-k8s = "your_package.addons:K8S_ADDON"
```

An entry point may resolve to a single `Component`, an iterable of them, or a
callable returning either. `pip install your-package` next to bootstrapper and
`bootstrapper list templates` shows it.

## Writing the files

**Contents.** A file ending `.j2` is rendered with Jinja and loses the suffix.
Anything else is copied byte for byte — that is how binary assets and files that
legitimately contain `{{ }}` (Alembic's `script.py.mako`) get through intact.

**Paths.** `__name__` markers, substituted only when a variable of that name
exists. `src/__package_name__/__init__.py.j2` becomes
`src/market_api/__init__.py`: the first marker is a variable, `__init__` is not.

**Variables.** Everything on `ProjectSpec`, including the derived `slug`,
`package_name`, `class_prefix` and `env_prefix`, plus:

| name | what it is |
| --- | --- |
| `uses_database` | `False` only when `database` is `none` |
| `has_addon('docker')` | is that addon in this selection |
| `components` | every component id being rendered, in order |
| `gh('secrets.TOKEN')` | emits `${{ secrets.TOKEN }}` for GitHub Actions |

Use `gh(...)` rather than `{% raw %}` in workflow files. A raw tag at the start
of a line loses its indentation to `lstrip_blocks`, which produces YAML that
looks right in the template and is broken in the output.

Undefined variables raise `RenderError` instead of rendering empty, so a typo
fails the generation rather than shipping a subtly broken project.

**Conditional files.** Small variations belong in `{% if %}` blocks inside the
file. Whole directories that should not exist at all belong in a `skip`
predicate on the component, where the condition is greppable Python:

```python
def _skip(context, path):
    if context["uses_database"]:
        return False
    return path.startswith(("migrations/", "alembic.ini"))
```

## Ordering and conflicts

- `order` — lower renders first. Templates use 0, infrastructure addons 10–30,
  deployment addons 40.
- `requires` — pulled in transitively, so `deploy-fly` alone still gets you the
  Dockerfile it deploys.
- `conflicts` — an explicit pairwise refusal.
- `group` — everything sharing a non-empty group is mutually exclusive. All
  deployment addons use `group="deploy"`, which is why two of them are rejected
  instead of generating two workflows that fight over the same service.
