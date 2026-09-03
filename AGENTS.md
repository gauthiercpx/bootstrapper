# AGENTS.md

Instructions for AI coding agents working in this repository. Claude Code
reads `CLAUDE.md` as well — see it for the full rationale behind the commit
policy below.

## Commands

```bash
make install   # editable install with dev dependencies
make check     # ruff + mypy --strict + pytest -- everything CI runs
```

Run `make check` before considering a change finished. `pytest` alone runs
tests only; `ruff check --output-format=github .` and `mypy src` isolate lint
and typecheck.

## Layout

`README.md` documents the architecture and how to add a template or addon in
depth. In short: `src/bootstrapper/core/` is the engine (spec, registry,
renderer, plan, generator); `src/bootstrapper/templates/` and
`src/bootstrapper/addons/` are directories of Jinja-templated files plus a
small `__init__.py` declaring what they are. `docs/plugins.md` covers
extending the registry, including from a third-party package.

## Conventions

- Ruff (`select = ["E","F","I","UP","B","SIM"]`) and `mypy --strict` both run
  in CI; a change that fails either is not done.
- `tests/test_generator.py` renders every template across every addon and
  database combination and compiles/parses the output — a new template or
  addon is covered by those tests the moment it is registered.
- Template payloads under `*/files/` are Jinja sources, not importable Python
  or config to lint directly; ruff and mypy exclude them on purpose.

## Commits

Every commit must be authored and committed with:

```
user.name  = gauthiercpx
user.email = gauthier.coppeaux@gmail.com
```

Do not add `Co-Authored-By:` trailers, `Claude-Session:` trailers, or any
other assistant attribution to commit messages, PR titles, PR bodies, or code
comments — see `CLAUDE.md` for why this matters for GitHub's author linkage.
