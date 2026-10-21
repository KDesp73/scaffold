"""Tests for the command line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from scaffold.cli import cmd_new, parse_cli
from scaffold.interactive import validate_name


def test_parse_cli_reads_new_arguments() -> None:
    args = parse_cli(["new", "myproj", "--type", "cli", "--deps", "cli.h,logging.h"])

    assert args.cmd == "new"
    assert args.name == "myproj"
    assert args.type == "cli"
    assert args.deps == "cli.h,logging.h"


def test_parse_cli_requires_a_type() -> None:
    with pytest.raises(SystemExit):
        parse_cli(["new", "myproj"])


def test_parse_cli_rejects_unknown_type() -> None:
    with pytest.raises(SystemExit):
        parse_cli(["new", "myproj", "--type", "nope"])


@pytest.mark.parametrize("name", ["proj", "my-proj", "my.proj", "my_proj", "p1"])
def test_validate_name_accepts_valid_names(name: str) -> None:
    validate_name(name)


@pytest.mark.parametrize("name", ["", ".hidden", "-leading", "with space", "with/slash"])
def test_validate_name_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError):
        validate_name(name)


def test_cmd_new_rejects_invalid_name(tmp_path: Path) -> None:
    args = parse_cli(["new", "bad name", "--type", "cli"])

    assert cmd_new(args) == 1


def test_cmd_new_refuses_to_overwrite_non_empty_directory(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("important", encoding="utf-8")

    args = parse_cli(["new", str(target), "--type", "cli"])

    assert cmd_new(args) == 1
    assert (target / "keep.txt").read_text(encoding="utf-8") == "important"
