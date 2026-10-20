"""
Struct Format:
#                                       -> comment (ignore)
!dep:                                   -> fixed dependency
?dep:                                   -> optional dependency
no prefix, with or without indentation  -> file | directory
"""

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
from typing import Literal


class ProjectType(Enum):
    LIBRARY = "library"
    CLI = "cli"
    WORKSPACE = "workspace"
    GUI = "gui"


@dataclass
class ProjectFile:
    absolute: str
    relative: str
    name: str
    type: Literal[
        "gitignore",
        "license",
        "main",
        "make",
        "readme",
        "unknown",
        "version",
    ]


class ProjectBuilder:
    def __init__(self, root: str, project_type: ProjectType):
        self.root = root
        self.type = project_type

    def _recipe(self) -> str:
        structfile = f"structs/{self.type.value}.struct"
        with open(structfile, "r", encoding="utf-8") as file:
            return file.read()

    def _get_file_type(self, name: str) -> str:
        """Helper to map filename to allowed ProjectFile type literals."""
        lower = name.lower()
        if "gitignore" in lower:
            return "gitignore"
        elif "license" in lower:
            return "license"
        elif "main" in lower:
            return "main"
        elif "make" in lower:
            return "make"
        elif "readme" in lower:
            return "readme"
        elif "version" in lower:
            return "version"
        return "unknown"

    def _get_content(self, filename: str, **kwargs) -> str:
        from jinja2 import Template

        with open(f"templates/{filename}.jinja") as file:
            template_string = file.read()

        template = Template(template_string)
        return template.render(kwargs)

    def structure(self) -> tuple[list[ProjectFile], list[str], list[str]]:
        recipe = self._recipe()
        lines = recipe.split("\n")

        files: list[ProjectFile] = []
        dirs: list[str] = []
        dependencies: list[str] = []
        
        path_stack: list[tuple[int, str]] = []

        for line in lines:
            if not line.strip() or line.strip().startswith("#"):
                continue

            stripped = line.strip()

            # Handle dependencies (!dep: and ?dep:)
            if stripped.startswith(("!dep:", "?dep:")):
                dep_name = stripped.split(":", 1)[1].strip()
                dependencies.append(dep_name)
                continue

            # Calculate indentation level (number of leading spaces)
            indent = len(line) - len(line.lstrip(" "))

            # Pop stack items that are at or deeper than the current indent level
            while path_stack and path_stack[-1][0] >= indent:
                path_stack.pop()

            is_dir = stripped.endswith("/")
            name = stripped.rstrip("/")

            path_stack.append((indent, name))

            # Build relative and absolute paths using the path stack
            rel_parts = [p[1] for p in path_stack]
            relative_path = os.path.join(*rel_parts)
            absolute_path = os.path.join(self.root, relative_path)

            if is_dir:
                dirs.append(relative_path)
            else:
                project_file = ProjectFile(
                    absolute=absolute_path,
                    relative=relative_path,
                    name=name,
                    type=self._get_file_type(name),
                )
                files.append(project_file)

        return files, dirs, dependencies

    def create(self, files: list[ProjectFile], dirs: list[str], dependencies: list[str]):
        """Creates the parsed directories and files on disk."""
        for rel_dir in dirs:
            abs_dir = os.path.join(self.root, rel_dir)
            os.makedirs(abs_dir, exist_ok=True)

        # Prepare template context variables based on parsed dependencies
        template_context = {
            "dep_cli": "cli.h" in dependencies,
            "dep_logging": "logging.h" in dependencies,
            "name": self.root,
        }

        for project_file in files:
            parent_dir = os.path.dirname(project_file.absolute)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # Determine template name based on file type or name
            # e.g., main.c -> main.c, Makefile -> Makefile
            template_name = project_file.name
            
            # Optional: handle files that might not have a template yet gracefully
            try:
                rendered = self._get_content(template_name, **template_context)
            except FileNotFoundError:
                rendered = ""  # Fallback to empty file if no template exists

            with open(project_file.absolute, "w", encoding="utf-8") as f:
                f.write(rendered)

        print(f"Successfully created {len(dirs)} directories and {len(files)} files.")


if __name__ == "__main__":
    builder = ProjectBuilder(
        root="./example",
        project_type=ProjectType.WORKSPACE
    )
    
    files, dirs, dependencies = builder.structure()
    print(f"Parsed: {len(dirs)} dirs, {len(files)} files, {len(dependencies)} deps.")

    builder.create(files, dirs, dependencies)
