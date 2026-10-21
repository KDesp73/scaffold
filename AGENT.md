You are an expert systems developer and Python automation engineer. Your task is to build a robust, command-line C project scaffolding tool in Python. 

This tool will automate the creation of new C projects, support different project types, and handle custom Makefile-based workflows without relying on CMake.

---

### 1. Core Requirements & Architecture

* **Language:** Python 3.11+ (using modern type hints, `pathlib` for path manipulation, and `argparse` or `click` for the CLI interface).
* **Build System Philosophy:** Pure Makefiles. **No CMake, no automake.** The generated projects must rely on clean, hand-written or templated Makefiles with automatic dependency tracking (`-MMD -MP`).
* **Modularity:** The tool must be modular so adding new project types or libraries is straightforward.

---

### 2. Supported Project Types & Structures

Your tool should accept a project type argument and generate the corresponding directory tree and template files:

1. **Library (`--type lib`)**
   ```text
   project_name/
   ├── Makefile
   ├── include/
   │   ├── header2.h
   │   └── header1.h
   ├── src/
   │   ├── file2.c
   │   └── file1.c
   ├── tests/
   │   └── test1.c
   └── README.md

```

2. **CLI Application (`--type cli`)**
```text
project_name/
├── Makefile
├── include/
│   ├── header2.h
│   └── header1.h
├── src/
│   ├── file1.c
│   └── main.c
└── README.md

```


3. **Workspace / Monorepo (`--type workspace`)**
```text
workspace_name/
├── Makefile            # Root orchestrator
├── libs/
│   └── core_lib/       # Shared library template
├── include/
│   ├── header2.h
│   └── header1.h
├── src/
│   ├── file2.c
│   └── file1.c
├── tests/
│   └── test1.c
└── apps/
    ├── gui/main.c
    ├── test/main.c
    ├── bench/main.c
    └── cli/main.c        # CLI app template linking to core_lib

```

---

### 3. Dependency Management Strategy (Makefile-Compatible)

Since the projects use custom Makefiles, the tool must handle external libraries using one of two automated approaches:

* **Header-only / Single-file libraries:** Automatically download or copy source files into a `deps/` or `vendor/` directory during scaffolding.
* **Git Submodules / Clone scripts:** Generate a Makefile target (`make fetch` or `make deps`) that automatically pulls required repositories via `git submodule add` or `git clone` into a local vendor folder, updating include flags (`-Ivendor/...`) accordingly.

---

### 4. Makefile Template Requirements

The generated `Makefile` must be production-ready for standard GNU Make:

* Support variables for `CC`, `CFLAGS`, `LDFLAGS`, `SRC`, `OBJ`, `DEP`, and `TARGET`.
* Enable automatic dependency generation using `gcc -MMD -MP` and include them via `-include $(DEP)`.
* Provide standard targets: `all`, `clean`, and optionally a debug/release profile flag.
* For whichever app is defined in `apps` we should be able to build it with `make <app-name>`

---

### 5. Expected Deliverables

Please implement this tool with the following components:

1. **Project CLI Interface:** A clean command-line entry point (e.g., `scaffold new <name> --type <cli|lib|gui|workspace> [--deps <lib1,lib2>]`).
2. **Template Engine:** A built-in mechanism (Python string formatting or Jinja-like templates) to populate `main.c`, header files with proper include guards, and the `Makefile`.
3. **File Generation Logic:** Safe directory and file creation using `pathlib`.
4. **Setup Guide / `README.md`:** A quick instruction set on how to install and run your scaffolding script.

### Last Notes

- If necessary we can have a `make` directory which will hold `.mk` files for better organization
- Use the following format for PHONY make rules
    ```make
    .PHONY: help
    help: ## Show this help message
        @echo "Available commands:"
        @grep -h -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
            awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

    .PHONY: build
    build: ## Build the python package
        pip install build
        python -m build
    ```
- This is the current c-starter repo I'm using: https://github.com/KDesp73/c-starter. Use it as reference
