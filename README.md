# bootstrapper

A modular CLI that generates a new project you can push, build and deploy the
same day: source skeleton, GitHub Actions and a deployment target.

Python is the first language it templates. The engine has nothing
Python-specific in it, so a `node-service` or `go-service` template is a
directory of files and one small module — not a rewrite.

```bash
pip install -e .
bootstrapper new "Market API" --owner gauthiercpx
```

```
✓ created Market API (28 files) in /home/you/market-api
  git init (branch main)
  git commit -m "chore: initial project skeleton"
╭─ next steps ─────────────────────────────────────────────╮
│ $ cd market-api                                          │
│ $ gh repo create gauthiercpx/market-api --public …       │
│ $ make install                                           │
│ $ make up                                                │
│ $ make test                                              │
╰──────────────────────────────────────────────────────────╯
```

## What you get

The `python-service` template generates a FastAPI service that is already
wired end to end — not a `hello world` you have to grow:

- **FastAPI** application factory, lifespan-managed resources, CORS
- **async SQLAlchemy 2.0** with one transaction per request, plus a worked CRUD
  resource so the HTTP → validation → session → database path is real and tested
- **Alembic** reading its URL from the app's settings, so migrations always
  target the same database the app does, and no credential lands in a file
- **Settings** from the environment via pydantic-settings, namespaced per project
- **Logging** that is readable locally and JSON in production
- **pytest** running against SQLite in memory — `make test` works with nothing
  else running
- `/health/live` and `/health/ready`, split so an orchestrator can tell
  "restart me" from "don't route to me yet"

Addons layer on top:

| addon | what it adds |
| --- | --- |
| `docker` | multi-stage Dockerfile (non-root, healthcheck) and a compose stack with Postgres |
| `github-actions` | CI: lint, typecheck, tests, migrations apply, image builds. Plus Dependabot |
| `pre-commit` | ruff and hygiene hooks |
| `deploy-ghcr` | build and push to ghcr.io on the default branch and tags |
| `deploy-azure-aca` | push to ACR and roll out to Azure Container Apps |
| `deploy-fly` | `fly.toml` and a deploy workflow |

Deployment addons are mutually exclusive — they share the `deploy` group, and
the registry rejects a selection with two of them rather than generating two
workflows that fight over the same service.

## Usage

```bash
bootstrapper list templates
bootstrapper list addons --template python-service
bootstrapper describe python-service

# Pick your own addon set instead of the template defaults
bootstrapper new "Market API" -a docker -a github-actions -a deploy-fly

# See exactly what would be written, write nothing
bootstrapper new "Market API" --dry-run

# No database, no persistence layer generated at all
bootstrapper new "Webhook Relay" --db none
```

Useful flags: `--template/-t`, `--addon/-a` (repeatable),
`--no-default-addons`, `--db {postgres,sqlite,none}`, `--python 3.12`,
`--license`, `--owner`, `--branch`, `--output/-o`, `--dry-run`, `--force`,
`--no-git`, `--yes`.

## The spec

Every generation is described by one object, `ProjectSpec`. The CLI builds one
from your flags; nothing downstream knows it came from a terminal.

```bash
bootstrapper new "Market API" --db sqlite --print-spec > market-api.json
bootstrapper new --spec market-api.json
```

That is also the seam for a UI. `bootstrapper schema` prints the JSON Schema of
`ProjectSpec` — enough to render a form — and a web front end would validate the
posted JSON into the same model and call the same two functions the CLI calls:

```python
from bootstrapper.core import ProjectSpec, build_plan, generate

spec = ProjectSpec(name="Market API", addons=["docker", "github-actions"])
plan = build_plan(spec)  # rendered in memory, nothing touched
generate(spec, Path("/tmp/out"))  # writes it
```

`build_plan` returning a full in-memory `Plan` is what makes `--dry-run` honest:
it runs the real render and only skips the write.

## Architecture

```
src/bootstrapper/
  cli.py                 presentation only: prompts, tables, exit codes
  core/
    spec.py              ProjectSpec — the contract every front end speaks
    component.py         Template and Addon: a directory of files + metadata
    registry.py          discovery, dependency and conflict resolution
    renderer.py          Jinja for contents, __markers__ for paths
    plan.py              FileAction / Plan, and applying it to disk
    generator.py         spec + registry -> plan -> disk
    vcs.py               git init, commit, optional `gh repo create`
  templates/python_service/files/…
  addons/*/files/…
```

Templates and addons are the same shape on purpose: the generator renders
`[template, *addons]` in order, and a later component overriding an earlier
file is a supported move that the CLI reports rather than hides.

## Writing a template

1. `src/bootstrapper/templates/my_template/files/` — the payload.
2. `__init__.py` declaring a `Template` and exporting `COMPONENTS`.

Two substitution rules:

- **contents**: files ending `.j2` are rendered with Jinja (the suffix is
  stripped). Anything else is copied byte for byte, so binary assets and files
  containing `{{ }}` survive intact.
- **paths**: `__package_name__` style markers, e.g.
  `src/__package_name__/main.py.j2`. Jinja braces are kept out of path names
  because they confuse shells and editors.

Undefined variables raise instead of rendering empty — a typo fails the
generation rather than shipping a broken project.

Third-party packages can register their own without touching this repo, via the
`bootstrapper.templates` and `bootstrapper.addons` entry point groups:

```toml
[project.entry-points."bootstrapper.templates"]
my-template = "my_package:COMPONENTS"
```

## Development

```bash
make install
make check     # ruff + mypy + pytest
```

## Status

v0.1.0. One template, six addons, CLI only. The web UI is the next front end
over the same `core` — see `ProjectSpec` and `bootstrapper schema`.
