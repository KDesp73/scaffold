"""Interactive mode.

Run `scaffold` with no arguments and it guides the user through a few
questions until there is enough information to create the project:

1. project name
2. project type
3. which of the type's optional dependencies to install
4. any extra (of the available) dependencies they want
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scaffold.store import Store
from scaffold.structure import ProjectBuilder, ProjectType

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Order shown in the type menu (inline and plain)
TYPE_ORDER = [
    ProjectType.CLI,
    ProjectType.LIBRARY,
    ProjectType.GUI,
    ProjectType.WORKSPACE,
]


class Cancelled(Exception):
    """Raised when the user aborts the wizard (Ctrl+C / Ctrl+D)."""


def validate_name(name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            "Use letters, digits, '.', '_' or '-' and start with a letter or digit."
        )


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Cancelled from None


def _ask_name() -> str:
    while True:
        name = _ask("Project name: ")
        if not name:
            print("[WARN] The name cannot be empty")
            continue
        try:
            validate_name(name)
        except ValueError as e:
            print(f"[WARN] {e}")
            continue
        root = Path(name)
        if root.exists() and any(root.iterdir()):
            print(f"[WARN] Directory '{root}' already exists and is not empty")
            continue
        return name


def _ask_type() -> ProjectType:
    print("Project type:")
    for i, ptype in enumerate(TYPE_ORDER, 1):
        print(f"  {i}) {ptype.value}")

    while True:
        answer = _ask(f"Choose [1-{len(TYPE_ORDER)} or name]: ").lower()
        for i, ptype in enumerate(TYPE_ORDER, 1):
            if answer == str(i) or answer == ptype.value:
                return ptype
        print(
            "[WARN] Choose one of: "
            + ", ".join(f"{i}) {t.value}" for i, t in enumerate(TYPE_ORDER, 1))
        )


def _ask_deps(label: str, options: list[str]) -> list[str]:
    """Ask the user to pick any of *options*, by number or by name.

    Empty input selects nothing. Re-prompts until the answer only contains
    valid choices. Order of the answer is preserved, duplicates dropped.
    """
    print(f"{label}:")
    for i, option in enumerate(options, 1):
        print(f"  {i}) {option}")

    while True:
        answer = _ask("Select (numbers or names, comma-separated, Enter = none): ")
        if not answer:
            return []

        picked: list[str] = []
        for token in re.split(r"[,\s]+", answer):
            if not token:
                continue
            if token.isdigit():
                index = int(token)
                choice = options[index - 1] if 1 <= index <= len(options) else None
            else:
                choice = next(
                    (o for o in options if o.lower() == token.lower()), None
                )
            if choice is None:
                print(f"[WARN] '{token}' is not one of: {', '.join(options)}")
                break
            if choice not in picked:
                picked.append(choice)
        else:
            # no break: every token was valid
            return picked


def run_wizard() -> argparse.Namespace | None:
    """Ask questions until a project can be created.

    On a TTY this shows inline "pretty menus" in the style of the
    ``npx create-*`` tools (:mod:`scaffold.menus`); on pipes/CI — or when
    the terminal cannot drive them — it falls back to plain line prompts.

    Returns the arguments for `cli.cmd_new`, or None if the user cancelled.
    """
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            from scaffold import menus  # deferred: menus imports this module
        except ImportError:
            pass  # termios/tty not available (e.g. bare Windows)
        else:
            if menus.AVAILABLE:
                try:
                    return menus.run()
                except menus.Unavailable as e:
                    print(f"[WARN] Menus unavailable ({e}), using plain prompts\n")

    return _run_plain()


def _run_plain() -> argparse.Namespace | None:
    """Line-based prompts for non-TTY sessions and menu fallbacks."""
    print("Interactive setup — answer the questions to create your project.")
    print("(Ctrl+C aborts)\n")

    try:
        name = _ask_name()

        print()
        project_type = _ask_type()

        builder = ProjectBuilder(root=name, project_type=project_type)
        _, _, struct_deps = builder.structure()
        fixed = [d.name for d in struct_deps if d.required]
        optional = [d.name for d in struct_deps if not d.required]

        selected: list[str] = []
        if optional:
            print(f"\nType '{project_type.value}' has optional dependencies:")
            selected = _ask_deps("Optional dependencies to install", optional)
        else:
            print(f"\nType '{project_type.value}' has no optional dependencies")

        # Everything the store still offers (fixed + already selected excluded)
        pool = [k for k in Store() if k not in set(fixed) | set(selected)]
        extra: list[str] = []
        if pool:
            print()
            extra = _ask_deps("Extra dependencies from the store", pool)

        chosen = selected + extra

        print("\nSummary:")
        print(f"  name:     {name}")
        print(f"  type:     {project_type.value}")
        print(f"  location: {Path(name)}")
        print(f"  deps:     {', '.join(fixed + chosen) if fixed or chosen else '(none)'}")

        if _ask("Create this project? [Y/n]: ").lower() not in ("", "y", "yes"):
            print("[INFO] Cancelled")
            return None
    except Cancelled:
        print("[INFO] Cancelled")
        return None

    return argparse.Namespace(
        name=name,
        type=project_type.value,
        deps=",".join(chosen) if chosen else None,
    )
