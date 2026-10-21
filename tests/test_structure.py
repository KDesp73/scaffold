"""Tests for struct parsing and project scaffolding."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scaffold.store import Store
from scaffold.structure import (
    ProjectBuilder,
    ProjectType,
    _guard_for,
    active_dep_stems,
)


def _relative_paths(files) -> list[str]:
    return sorted(f.relative.as_posix() for f in files)


def test_structure_parses_cli_recipe(tmp_path: Path) -> None:
    builder = ProjectBuilder(root=tmp_path, project_type=ProjectType.CLI)

    files, dirs, _deps = builder.structure()

    assert _relative_paths(files) == [
        ".gitignore",
        "Makefile",
        "README.md",
        "include/header1.h",
        "include/header2.h",
        "include/version.h",
        "src/file1.c",
        "src/file2.c",
        "src/main.c",
    ]
    assert sorted(d.as_posix() for d in dirs) == ["include", "src"]


def test_structure_marks_required_and_optional_deps(tmp_path: Path) -> None:
    builder = ProjectBuilder(root=tmp_path, project_type=ProjectType.CLI)

    _, _, deps = builder.structure()

    by_name = {d.name: d.required for d in deps}
    assert by_name == {"cli.h": True, "ansi.h": True, "logging.h": False}


def test_structure_uses_nested_paths(tmp_path: Path) -> None:
    builder = ProjectBuilder(root=tmp_path, project_type=ProjectType.WORKSPACE)

    files, dirs, _ = builder.structure()

    assert any(f.relative.as_posix().count("/") >= 1 for f in files)
    assert dirs


def test_structure_raises_for_unknown_type(tmp_path: Path) -> None:
    builder = ProjectBuilder(root=tmp_path, project_type=ProjectType.CLI)
    # A type whose struct file does not exist in the package.
    builder.type = SimpleNamespace(value="not-a-real-type")

    with pytest.raises(FileNotFoundError):
        builder.structure()


def test_guard_for_is_uppercase_sanitised() -> None:
    assert _guard_for("version.h") == "VERSION_H_H"
    assert _guard_for("main.c") == "MAIN_C_H"
    assert _guard_for("a-b.c") == "A_B_C_H"


def test_active_dep_stems_strips_extensions() -> None:
    assert active_dep_stems(["cli.h", "raylib"]) == ["cli", "raylib"]


def test_create_writes_rendered_files(tmp_path: Path) -> None:
    # An empty store keeps the test offline: no dependency is ever fetched.
    store = Store(root=tmp_path / "empty-store")
    root = tmp_path / "proj"
    builder = ProjectBuilder(root=root, project_type=ProjectType.CLI, store=store)

    files, dirs, deps = builder.structure()
    builder.create(files, dirs, deps)

    assert (root / "src").is_dir()
    assert (root / "include").is_dir()
    assert (root / "src" / "main.c").is_file()
    assert (root / "Makefile").is_file()
    assert (root / "src" / "main.c").read_text(encoding="utf-8").strip() != ""
