import argparse


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description="Opinionated C project starter",
        # color=False
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Command to execute")

    new_parser = subparsers.add_parser("new", help="Create a new project")
    new_parser.add_argument("name", help="Name of the new project")
    new_parser.add_argument(
        "--type",
        choices=["cli", "lib", "gui", "workspace"],
        required=True,
        help="Type of project to create"
    )
    new_parser.add_argument(
        "--deps",
        help="Comma-separated list of dependencies (e.g., lib1,lib2)"
    )

    return parser.parse_args()


def main():
    args = parse_cli()
    print(f"Command: {args.cmd}")
    print(f"Project Name: {args.name}")
    print(f"Type: {args.type}")
    print(f"Deps: {args.deps}")

    return 0
