"""Plan behaviour: overrides are recorded, and applying is all-or-nothing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bootstrapper.core import FileAction, Plan, TargetExists


def _plan(*actions: FileAction) -> Plan:
    plan = Plan()
    for action in actions:
        plan.add(action)
    return plan


def test_later_component_overrides_and_the_override_is_recorded() -> None:
    plan = _plan(
        FileAction(path="Makefile", content=b"base", origin="template"),
        FileAction(path="Makefile", content=b"addon", origin="docker"),
    )

    assert plan.actions["Makefile"].text == "addon"
    assert plan.overrides == [("Makefile", "template", "docker")]


def test_apply_writes_nested_paths(tmp_path: Path) -> None:
    plan = _plan(FileAction(path="src/app/main.py", content=b"x = 1\n"))

    written = plan.apply(tmp_path)

    assert written == [tmp_path / "src/app/main.py"]
    assert (tmp_path / "src/app/main.py").read_text() == "x = 1\n"


def test_existing_files_stop_the_whole_apply(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("mine", encoding="utf-8")
    plan = _plan(
        FileAction(path="README.md", content=b"generated"),
        FileAction(path="new.py", content=b"generated"),
    )

    with pytest.raises(TargetExists, match="--force"):
        plan.apply(tmp_path)

    assert (tmp_path / "README.md").read_text() == "mine"
    assert not (tmp_path / "new.py").exists()  # nothing was written


def test_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("mine", encoding="utf-8")
    plan = _plan(FileAction(path="README.md", content=b"generated"))

    plan.apply(tmp_path, force=True)

    assert (tmp_path / "README.md").read_text() == "generated"


@pytest.mark.skipif(sys.platform == "win32", reason="NTFS has no POSIX executable bit")
def test_executable_bit_is_preserved(tmp_path: Path) -> None:
    plan = _plan(FileAction(path="run.sh", content=b"#!/bin/sh\n", executable=True))

    plan.apply(tmp_path)

    assert (tmp_path / "run.sh").stat().st_mode & 0o111


def test_tree_is_indented_by_depth() -> None:
    plan = _plan(
        FileAction(path="README.md", content=b""),
        FileAction(path="src/app/main.py", content=b""),
    )

    assert plan.tree().splitlines() == ["README.md", "src/", "  app/", "    main.py"]
