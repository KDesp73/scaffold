"""Struct Format:
#                                       -> comment (ignore)
!dep:                                   -> fixed dependency
?dep:                                   -> optional dependency
no prefix, with or without indentation  -> file | directory
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from scaffold.config import settings
from scaffold.resources import STRUCTS_DIR, TEMPLATES_DIR
from scaffold.store import Store


class ProjectType(Enum):
    LIBRARY = "lib"
    CLI = "cli"
    WORKSPACE = "workspace"
    GUI = "gui"


@dataclass
class ProjectFile:
    absolute: Path
    relative: Path
    name: str


@dataclass
class StructDep:
    name: str
    required: bool


def _guard_for(filename: str) -> str:
    """HEADER1_H, MAIN_C, ..."""
    return re.sub(r"[^0-9A-Za-z]", "_", filename).upper() + "_H"


class ProjectBuilder:
    def __init__(
        self,
        root: str | Path,
        project_type: ProjectType,
        deps: list[str] | None = None,
        store: Store | None = None,
    ):
        self.root = Path(root)
        self.type = project_type
        self.requested_deps = list(deps or [])
        self.store = store or Store()

        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def _recipe(self) -> str:
        structfile = STRUCTS_DIR / f"{self.type.value}.struct"
        if not structfile.is_file():
            raise FileNotFoundError(
                f"No struct file for project type '{self.type.value}' "
                f"(expected {structfile})"
            )
        return structfile.read_text(encoding="utf-8")

    def structure(self) -> tuple[list[ProjectFile], list[Path], list[StructDep]]:
        lines = self._recipe().split("\n")

        files: list[ProjectFile] = []
        dirs: list[Path] = []
        dependencies: list[StructDep] = []

        path_stack: list[tuple[int, str]] = []

        for line in lines:
            if not line.strip() or line.strip().startswith("#"):
                continue

            stripped = line.strip()

            # Handle dependencies (!dep: and ?dep:)
            if stripped.startswith(("!dep:", "?dep:")):
                dep_name = stripped.split(":", 1)[1].strip()
                dependencies.append(
                    StructDep(name=dep_name, required=stripped.startswith("!dep:"))
                )
                continue

            # Calculate indentation level (number of leading spaces)
            indent = len(line) - len(line.lstrip(" "))

            # Pop stack items that are at or deeper than the current indent level
            while path_stack and path_stack[-1][0] >= indent:
                path_stack.pop()

            is_dir = stripped.endswith("/")
            name = stripped.rstrip("/")

            path_stack.append((indent, name))

            relative = Path(*[p[1] for p in path_stack])

            if is_dir:
                dirs.append(relative)
            else:
                files.append(
                    ProjectFile(
                        absolute=self.root / relative,
                        relative=relative,
                        name=relative.name,
                    )
                )

        return files, dirs, dependencies

    def _template_candidates(self, relative: Path) -> list[str]:
        """Template lookup order, most specific first.

        1. templates/<type>/<full relative path>.jinja   (workspace/apps/cli/main.c.jinja)
        2. templates/<full relative path>.jinja          (src/main.c.jinja)
        3. templates/<type>/<basename>.jinja             (gui/main.c.jinja)
        4. templates/<basename>.jinja                    (main.c.jinja)
        """
        rel = relative.as_posix()
        t = self.type.value
        return [
            f"{t}/{rel}.jinja",
            f"{rel}.jinja",
            f"{t}/{relative.name}.jinja",
            f"{relative.name}.jinja",
        ]

    def _get_content(self, relative: Path, **context) -> str:
        for candidate in self._template_candidates(relative):
            try:
                template = self._env.get_template(candidate)
            except TemplateNotFound:
                continue
            return template.render(**context)

        print(f"[WARN] No template found for '{relative}', writing empty file")
        return ""

    def _active_deps(self, struct_deps: list[StructDep]) -> list[str]:
        """Fixed deps are always active; optional ones only if requested.
        Requested deps not mentioned in the struct are added too (if in store)."""
        active: list[str] = []

        def add(key: str) -> None:
            if key not in active:
                active.append(key)

        for dep in struct_deps:
            if dep.required or dep.name in self.requested_deps:
                add(dep.name)
        for key in self.requested_deps:
            if self.store.get(key) is None:
                print(f"[WARN] Dependency '{key}' not found in store, skipping")
                continue
            add(key)

        return active

    def create(
        self,
        files: list[ProjectFile],
        dirs: list[Path],
        struct_deps: list[StructDep],
    ) -> None:
        """Creates the parsed directories and files on disk."""
        for rel_dir in dirs:
            (self.root / rel_dir).mkdir(parents=True, exist_ok=True)

        deps_dir = settings.deps_dir
        active_deps = self._active_deps(struct_deps)

        # Actually download each dependency into the project's deps directory
        # (fetched once at scaffold time; nothing is copied into the project).
        for key in active_deps:
            if not self.store.fetch(key, self.root / deps_dir):
                print(
                    f"[WARN] Could not fetch dependency '{key}' — "
                    "the project may not build until it is available"
                )

        dep_cflags, dep_ldflags = self.store.dep_flags(active_deps, deps_dir)

        version = settings.default_version.split(".")
        if len(version) != 3:
            print(
                f"[WARN] default_version '{settings.default_version}' is not X.Y.Z, "
                "falling back to 0.1.0"
            )
            version = ["0", "1", "0"]

        base_context: dict = {
            "name": self.root.name,
            "type": self.type.value,
            "version": settings.default_version,
            "default_version_major": version[0],
            "default_version_minor": version[1],
            "default_version_patch": version[2],
            "deps_dir": deps_dir,
            "deps": active_deps,
            "dep_cflags": " ".join(dep_cflags),
            "dep_ldflags": " ".join(dep_ldflags),
        }
        for key in active_dep_stems(active_deps):
            base_context[f"dep_{key}"] = True

        for project_file in files:
            project_file.absolute.parent.mkdir(parents=True, exist_ok=True)

            context = dict(base_context)
            context["guard"] = _guard_for(project_file.name)

            # Files inside libs/<name>/ are part of that sub-library;
            # give templates the library's name, not the workspace's.
            parts = project_file.relative.parts
            if len(parts) >= 2 and parts[0] == "libs":
                context["name"] = parts[1]

            rendered = self._get_content(project_file.relative, **context)
            project_file.absolute.write_text(rendered, encoding="utf-8")

        print(
            f"Successfully created {len(dirs)} directories and {len(files)} files "
            f"in '{self.root}'."
        )


def active_dep_stems(deps: list[str]) -> list[str]:
    """'cli.h' -> 'cli', 'raylib' -> 'raylib'"""
    return [Path(dep).stem for dep in deps]
