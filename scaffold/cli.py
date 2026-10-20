import argparse


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description="Opinionated C project starter",
        color=False
    )

    parser.add_argument("cmd", help="Create a new project")

    return parser.parse_args()


def main() -> int:
    args = parse_cli()
    return 0
