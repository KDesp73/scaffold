# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.0] - 2026-10-21

### Added

- Initial implementation of the `scaffold` CLI, project templates and Makefile-based build
- Project generation from `.struct` structure files and Jinja2 templates
- Bundled dependency store with fetch scripts for `cli.h`, `ansi.h`, `logging.h` and `raylib`
- Packaging, CLI wiring, Makefiles and dependency support
- Dependencies are fetched at scaffold time into the configured `deps_dir`
- Interactive wizard when `scaffold` is run without arguments
- Inline `npx`-style pretty menus for the interactive wizard
- GitHub Actions CI workflow running lint, tests and build
- Ruff pinned as a development dependency

### Changed

- Config directory moved to `~/.config` and `cli.h` made a fixed dependency of workspaces
- CI now also tests Python 3.11, the minimum supported version

### Removed

- Removed the `AGENT.md` design specification

### Fixed

- YAML configuration loading (`scaffold.yaml`) and the `deps_dir` / `default_version` settings
- Pinned the Ruff rule set to resolve the CI lint failure


[0.1.0]: https://github.com/KDesp73/scaffold/releases/tag/v0.1.0

