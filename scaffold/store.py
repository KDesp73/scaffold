"""Dependency store.

Each directory inside the store is a package, keyed by its name. A package
may contain:

- `fetch`   : script that accepts the destination as the first argument,
              the version as the second (optional) and the platform as the
              third (optional).
- `flags`   : `CFLAGS`/`LDFLAGS` needed to use the library. `{deps}` is
              replaced with the project's deps directory. If missing, no
              flags are added to the build step.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from scaffold.resources import STORE_DIR


@dataclass
class Dependency:
    key: str
    path: Path

    @property
    def has_fetch(self) -> bool:
        return (self.path / "fetch").is_file()

    @property
    def has_flags(self) -> bool:
        return (self.path / "flags").is_file()


@dataclass
class Store:
    root: Path = field(default=STORE_DIR)
    registry: dict[str, Dependency] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> Store:
        self.registry.clear()
        if not self.root.is_dir():
            return self

        for entry in sorted(self.root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            self.registry[entry.name] = Dependency(key=entry.name, path=entry)
        return self

    def __iter__(self) -> Iterator[str]:
        """Iterate over the package keys, like the underlying registry."""
        return iter(self.registry)

    def keys(self) -> list[str]:
        return list(self)

    def get(self, key: str) -> Dependency | None:
        return self.registry.get(key)

    def fetch(
        self,
        key: str,
        destination: Path,
        version: str | None = None,
        platform: str | None = None,
    ) -> bool:
        """Run the package's fetch script to download the dependency.

        The script receives the destination as its first argument, followed
        by the optional version and platform. The script's output is streamed
        as-is. Returns False if the package is unknown, has no fetch script,
        or the script fails.
        """
        dep = self.get(key)
        if dep is None or not dep.has_fetch:
            return False

        if platform is not None and version is None:
            version = ""

        cmd = ["bash", str(dep.path / "fetch"), str(destination)]
        if version is not None:
            cmd.append(version)
        if platform is not None:
            cmd.append(platform)

        return subprocess.run(cmd, check=False).returncode == 0

    def dep_flags(self, keys: list[str], deps_dir: str) -> tuple[list[str], list[str]]:
        """Return (cflags, ldflags) for the given deps, `{deps}` substituted."""
        cflags: list[str] = []
        ldflags: list[str] = []

        for key in keys:
            dep = self.get(key)
            if dep is None or not dep.has_flags:
                continue
            for line in (dep.path / "flags").read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("CFLAGS="):
                    cflags.append(line.removeprefix("CFLAGS=").replace("{deps}", deps_dir))
                elif line.startswith("LDFLAGS="):
                    ldflags.append(line.removeprefix("LDFLAGS=").replace("{deps}", deps_dir))

        return cflags, ldflags


if __name__ == "__main__":
    store = Store()
    print(store.keys())
