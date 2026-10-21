import argparse
import re
import sys
from pathlib import Path

from scaffold.structure import ProjectBuilder, ProjectType

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description="Opinionated C project starter",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.1.0"
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Command to execute")

    new_parser = subparsers.add_parser("new", help="Create a new project")
    new_parser.add_argument("name", help="Name of the new project")
    new_parser.add_argument(
        "--type",
        choices=[t.value for t in ProjectType],
        required=True,
        help="Type of project to create",
    )
    new_parser.add_argument(
        "--deps",
        help="Comma-separated list of dependencies (e.g., cli.h,logging.h)",
    )

    return parser.parse_args(argv)


def validate_name(name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            "Use letters, digits, '.', '_' or '-' and start with a letter or digit."
        )


def cmd_new(args: argparse.Namespace) -> int:
    try:
        validate_name(args.name)
    except ValueError as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        return 1

    root = Path(args.name)
    if root.exists() and any(root.iterdir()):
        print(f"[ERRO] Directory '{root}' already exists and is not empty", file=sys.stderr)
        return 1

    deps = [d.strip() for d in args.deps.split(",") if d.strip()] if args.deps else []

    builder = ProjectBuilder(
        root=root,
        project_type=ProjectType(args.type),
        deps=deps,
    )
    files, dirs, struct_deps = builder.structure()
    builder.create(files, dirs, struct_deps)

    print(f"\nNext steps:\n  cd {root}\n  make help\n  make")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_cli(argv)

    if args.cmd == "new":
        return cmd_new(args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
