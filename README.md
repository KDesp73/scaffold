# scaffold

Opinionated C project starter — scaffolds pure-Makefile C projects (no CMake).

## Requirements

- Python 3.11+
- GNU Make
- A C compiler (`cc`/`gcc`/`clang`)
- `wget` (only for fetching dependencies at scaffold time)

## Install

```bash
pip install .            # regular install
# or, for development:
make dev                 # pip install -e .
```

Verify:

```bash
scaffold --version
scaffold --help
```

## Usage

```bash
scaffold new <name> --type <cli|lib|gui|workspace> [--deps <lib1,lib2>]
```

Examples:

```bash
scaffold new myapp  --type cli
scaffold new mylib  --type lib
scaffold new mygui  --type gui
scaffold new myws   --type workspace
scaffold new myapp  --type cli --deps logging.h    # add optional deps
```

Dependencies are looked up in the bundled store (`cli.h`, `ansi.h`,
`logging.h`, `raylib`). Fixed (`!dep:`) dependencies of the chosen type are
always included; optional (`?dep:`) ones are only added when requested with
`--deps`. Each selected dependency's fetch script runs during
`scaffold new`, downloading it straight into the project's deps directory
(`deps/` by default, configurable via `deps_dir` in `scaffold.yaml`).

### What you get

```text
cli:      Makefile, include/{version,header1,header2}.h, src/{main,file1,file2}.c
lib:      as above + tests/ (builds .a and .so)
gui:      like cli, with raylib wired up
workspace: root Makefile orchestrating libs/ (core_lib) and apps/{cli,test,bench,gui}
```

Every project also ships `.gitignore` and `README.md`. Dependencies are
fetched into the deps directory while scaffolding, so they are ready to
build immediately and can be committed to version control.

## Building generated projects

```bash
cd <project>
make help        # list all targets (bare `make` does the same)
make             # same as `make help`
make all         # build
make test        # lib/workspace: build and run tests
make clean       # remove build artifacts
make all type=RELEASE   # optimized build (default is debug + sanitizers)
```

In a workspace, build a single app with `make <app-name>`:

```bash
make cli         # builds libs/core_lib first, then apps/cli -> build/cli
make bench
make all         # libs + all apps
```

## Development

```bash
make dev    # install in editable mode
make build  # build the package
make docs   # generate the documentation (requires tinydocs-cli)
```

See [AGENT.md](AGENT.md) for the design specification and [docs/References.md](docs/References.md) for useful references.
