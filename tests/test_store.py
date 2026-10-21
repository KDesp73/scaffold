"""Tests for the dependency store."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from scaffold.store import Store


def _make_package(root: Path, name: str, *, flags: str | None = None) -> Path:
    """Create a fake package directory inside `root` and return its path."""
    pkg = root / name
    pkg.mkdir(parents=True)
    if flags is not None:
        (pkg / "flags").write_text(flags, encoding="utf-8")
    return pkg


def test_load_discovers_packages(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha")
    _make_package(tmp_path, "beta")

    store = Store(root=tmp_path)

    assert store.keys() == ["alpha", "beta"]
    assert store.get("alpha") is not None
    assert store.get("alpha").path == tmp_path / "alpha"
    assert store.get("missing") is None


def test_load_skips_hidden_entries(tmp_path: Path) -> None:
    _make_package(tmp_path, ".internal")
    _make_package(tmp_path, "visible")

    store = Store(root=tmp_path)

    assert store.keys() == ["visible"]


def test_load_on_missing_root_is_empty(tmp_path: Path) -> None:
    store = Store(root=tmp_path / "does-not-exist")

    assert store.keys() == []
    assert store.get("anything") is None


def test_store_is_iterable_over_keys(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha")
    _make_package(tmp_path, "beta")

    store = Store(root=tmp_path)

    assert list(store) == store.keys() == ["alpha", "beta"]


def test_dependency_flags_are_detected(tmp_path: Path) -> None:
    _make_package(tmp_path, "withflags", flags="CFLAGS=-DFOO\n")
    _make_package(tmp_path, "noflags")

    store = Store(root=tmp_path)

    assert store.get("withflags").has_flags is True
    assert store.get("withflags").has_fetch is False
    assert store.get("noflags").has_flags is False


def test_dep_flags_substitutes_deps_dir(tmp_path: Path) -> None:
    _make_package(
        tmp_path,
        "alpha",
        flags="CFLAGS=-I{deps}/include\nLDFLAGS=-L{deps}/lib\n",
    )

    store = Store(root=tmp_path)
    cflags, ldflags = store.dep_flags(["alpha"], "deps")

    assert cflags == ["-Ideps/include"]
    assert ldflags == ["-Ldeps/lib"]


def test_dep_flags_ignores_unknown_and_flagless_packages(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha", flags="CFLAGS=-DFOO\n")
    _make_package(tmp_path, "plain")

    store = Store(root=tmp_path)
    cflags, ldflags = store.dep_flags(["alpha", "plain", "missing"], "deps")

    assert cflags == ["-DFOO"]
    assert ldflags == []


def _write_fetch_script(pkg: Path, exit_code: int) -> None:
    script = pkg / "fetch"
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


@pytest.mark.skipif(os.name == "nt", reason="requires a POSIX shell")
def test_fetch_returns_true_on_success(tmp_path: Path) -> None:
    pkg = _make_package(tmp_path, "alpha")
    _write_fetch_script(pkg, 0)

    store = Store(root=tmp_path)

    assert store.fetch("alpha", tmp_path / "dest") is True


@pytest.mark.skipif(os.name == "nt", reason="requires a POSIX shell")
def test_fetch_returns_false_on_failure(tmp_path: Path) -> None:
    pkg = _make_package(tmp_path, "alpha")
    _write_fetch_script(pkg, 1)

    store = Store(root=tmp_path)

    assert store.fetch("alpha", tmp_path / "dest") is False


def test_fetch_returns_false_without_fetch_script(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha")

    store = Store(root=tmp_path)

    assert store.fetch("alpha", tmp_path / "dest") is False


def test_fetch_returns_false_for_unknown_package(tmp_path: Path) -> None:
    store = Store(root=tmp_path)

    assert store.fetch("nope", tmp_path / "dest") is False
