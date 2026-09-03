"""Git/GitHub steps: every branch driven deterministically via the `_run` seam.

`create_github_repository` must never be exercised against the real `gh` CLI in
tests -- it would create an actual repository under whoever is logged in. `_run`
is the one seam the module offers for that, so tests patch it instead of
letting anything shell out.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bootstrapper.core.vcs import (
    create_github_repository,
    gh_available,
    git_available,
    init_repository,
)


def _completed(returncode: int, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


def test_git_available_reflects_which(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.shutil.which", lambda _: None)
    assert git_available() is False

    monkeypatch.setattr("bootstrapper.core.vcs.shutil.which", lambda _: "/usr/bin/git")
    assert git_available() is True


def test_gh_available_reflects_which(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.shutil.which", lambda _: None)
    assert gh_available() is False


def test_init_repository_warns_when_git_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.git_available", lambda: False)

    result = init_repository(tmp_path)

    assert not result.initialized
    assert "git not found" in result.warnings[0]


def test_init_repository_leaves_existing_repo_untouched(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    result = init_repository(tmp_path)

    assert not result.initialized
    assert "already a git repository" in result.warnings[0]


def test_init_repository_reports_init_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.git_available", lambda: True)
    monkeypatch.setattr(
        "bootstrapper.core.vcs._run", lambda args, cwd: _completed(1, "fatal: boom")
    )

    result = init_repository(tmp_path)

    assert not result.initialized
    assert "git init failed: fatal: boom" in result.warnings[0]


def test_init_repository_reports_add_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.git_available", lambda: True)
    calls = iter([_completed(0), _completed(1)])
    monkeypatch.setattr("bootstrapper.core.vcs._run", lambda args, cwd: next(calls))

    result = init_repository(tmp_path)

    assert result.initialized  # init succeeded before add failed
    assert not result.committed
    assert "git add failed" in result.warnings[0]


def test_init_repository_reports_commit_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.git_available", lambda: True)
    calls = iter([_completed(0), _completed(0), _completed(1, "user.email missing\n")])
    monkeypatch.setattr("bootstrapper.core.vcs._run", lambda args, cwd: next(calls))

    result = init_repository(tmp_path)

    assert result.initialized
    assert not result.committed
    assert "initial commit skipped" in result.warnings[0]


def test_init_repository_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.git_available", lambda: True)
    monkeypatch.setattr("bootstrapper.core.vcs._run", lambda args, cwd: _completed(0))

    result = init_repository(tmp_path, branch="trunk")

    assert result.initialized
    assert result.committed
    assert not result.warnings
    assert result.steps == [
        "git init (branch trunk)",
        'git commit -m "chore: initial project skeleton"',
    ]


def test_create_github_repository_warns_when_gh_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.gh_available", lambda: False)

    result = create_github_repository(tmp_path, owner="", name="demo")

    assert result.remote_url == ""
    assert "not found" in result.warnings[0]


def test_create_github_repository_reports_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.gh_available", lambda: True)
    monkeypatch.setattr(
        "bootstrapper.core.vcs._run", lambda args, cwd: _completed(1, "already exists")
    )

    result = create_github_repository(tmp_path, owner="gauthiercpx", name="demo")

    assert result.remote_url == ""
    assert "gh repo create failed: already exists" in result.warnings[0]


def test_create_github_repository_uses_owner_slug_and_records_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.gh_available", lambda: True)
    captured: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        captured.append(args)
        return _completed(0)

    monkeypatch.setattr("bootstrapper.core.vcs._run", fake_run)

    result = create_github_repository(tmp_path, owner="gauthiercpx", name="demo", private=False)

    assert result.remote_url == "https://github.com/gauthiercpx/demo"
    assert result.steps == ["gh repo create gauthiercpx/demo", "git push -u origin HEAD"]
    assert captured[0][:4] == ["gh", "repo", "create", "gauthiercpx/demo"]
    assert "--public" in captured[0]
    assert "--push" in captured[0]


def test_create_github_repository_without_owner_or_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bootstrapper.core.vcs.gh_available", lambda: True)
    captured: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        captured.append(args)
        return _completed(0)

    monkeypatch.setattr("bootstrapper.core.vcs._run", fake_run)

    result = create_github_repository(tmp_path, owner="", name="demo", push=False)

    assert result.remote_url == "https://github.com/demo"
    assert result.steps == ["gh repo create demo"]
    assert "--push" not in captured[0]
    assert "--private" in captured[0]
