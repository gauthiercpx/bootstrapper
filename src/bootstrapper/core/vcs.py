"""Git and GitHub steps that run after the files exist.

Everything here is best-effort and reported, never fatal: a generated project is
still a valid project if `git` is missing or the user is offline. The CLI shows
what succeeded and what was skipped.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

INITIAL_COMMIT_MESSAGE = "chore: initial project skeleton"


@dataclass
class GitResult:
    """Outcome of the post-generation VCS steps."""

    initialized: bool = False
    committed: bool = False
    remote_url: str = ""
    steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # Fixed argv, no shell.
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603


def git_available() -> bool:
    return shutil.which("git") is not None


def init_repository(destination: Path, *, branch: str = "main") -> GitResult:
    """`git init` + stage everything + one initial commit."""
    result = GitResult()
    if not git_available():
        result.warnings.append("git not found on PATH; skipped repository initialisation")
        return result
    if (destination / ".git").exists():
        result.warnings.append("destination is already a git repository; left untouched")
        return result

    completed = _run(["git", "init", "--initial-branch", branch], destination)
    if completed.returncode != 0:
        result.warnings.append(f"git init failed: {completed.stderr.strip()}")
        return result
    result.initialized = True
    result.steps.append(f"git init (branch {branch})")

    if _run(["git", "add", "-A"], destination).returncode != 0:
        result.warnings.append("git add failed; files were written but nothing is staged")
        return result

    commit = _run(["git", "commit", "-m", INITIAL_COMMIT_MESSAGE], destination)
    if commit.returncode != 0:
        # Almost always a missing user.email/user.name — worth saying out loud.
        result.warnings.append(f"initial commit skipped: {commit.stderr.strip().splitlines()[-1:]}")
        return result
    result.committed = True
    result.steps.append(f'git commit -m "{INITIAL_COMMIT_MESSAGE}"')
    return result


def gh_available() -> bool:
    return shutil.which("gh") is not None


def create_github_repository(
    destination: Path,
    *,
    owner: str,
    name: str,
    private: bool = True,
    push: bool = True,
) -> GitResult:
    """Create the remote via the `gh` CLI and push the first commit.

    Uses `gh` rather than a token of our own so the user's existing GitHub
    authentication is the only credential involved.
    """
    result = GitResult()
    if not gh_available():
        result.warnings.append(
            "GitHub CLI (`gh`) not found; create the repo manually and run "
            "`git remote add origin <url> && git push -u origin HEAD`"
        )
        return result

    slug = f"{owner}/{name}" if owner else name
    args = [
        "gh",
        "repo",
        "create",
        slug,
        "--private" if private else "--public",
        "--source",
        ".",
        "--remote",
        "origin",
    ]
    if push:
        args.append("--push")

    completed = _run(args, destination)
    if completed.returncode != 0:
        result.warnings.append(f"gh repo create failed: {completed.stderr.strip()}")
        return result

    result.remote_url = f"https://github.com/{slug}"
    result.steps.append(f"gh repo create {slug}")
    if push:
        result.steps.append("git push -u origin HEAD")
    return result
